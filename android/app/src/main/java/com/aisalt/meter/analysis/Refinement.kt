package com.aisalt.meter.analysis

import kotlinx.serialization.Serializable
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.sqrt

/**
 * Repeatability of one salinity reading (1σ, %p), from the R7.1 calibration triplicates:
 * ≈0.01–0.02 %p up to 1.1 %, ≈0.04 %p at 2.0 % (the response flattens near the top).
 */
object SalinityNoise {
    fun sigmaPct(pct: Double): Double = when {
        pct <= 1.1 -> 0.02
        pct >= 2.0 -> 0.045
        else -> 0.02 + (pct - 1.1) / 0.9 * 0.025
    }
}

enum class AdditionKind { SALT, WATER }

/** A measured addition: amount actually added and the salinity before / after mixing. */
@Serializable
data class AdditionRecord(
    val kind: String,          // AdditionKind name (kept as text for storage)
    val amount: Double,        // g of salt or mL of water
    val beforePct: Double,
    val afterPct: Double,
    val timeMillis: Long = 0,
) {
    val additionKind: AdditionKind get() = AdditionKind.valueOf(kind)
}

data class Estimate(val valueMl: Double, val relSigma: Double, val source: String) {
    val sigmaMl: Double get() = valueMl * relSigma
}

/** Method D: broth volume from salinity alone, around a known addition. */
object BackCalc {
    /**
     * Broth volume **after** the addition, with its relative uncertainty, or null when
     * the salinity change is too small to use.
     *  salt : W = ΔS·V·K            → V = W / (K·ΔS)
     *  water: S2 = S1·V0/(V0+ΔV)    → V0 = ΔV·S2/(S1−S2), after = V0 + ΔV
     */
    fun brothAfter(record: AdditionRecord, k: Double = SaltGuide.K_DEFAULT): Estimate? {
        val s1 = record.beforePct
        val s2 = record.afterPct
        val sig1 = SalinityNoise.sigmaPct(s1)
        val sig2 = SalinityNoise.sigmaPct(s2)
        return when (record.additionKind) {
            AdditionKind.SALT -> {
                val ds = s2 - s1
                if (ds < 3 * sqrt(sig1 * sig1 + sig2 * sig2) || record.amount <= 0) return null
                val liters = record.amount / (k * ds)
                Estimate(liters * 1000.0, sqrt(sig1 * sig1 + sig2 * sig2) / ds, "salt back-calculation")
            }
            AdditionKind.WATER -> {
                val drop = s1 - s2
                if (drop < 3 * sqrt(sig1 * sig1 + sig2 * sig2) || record.amount <= 0 || s2 <= 0) return null
                val before = record.amount * s2 / drop
                // σV0 = ΔV·sqrt((S2·σ1)² + (S1·σ2)²)/(S1−S2)²
                val sigmaBefore = record.amount * sqrt((s2 * sig1) * (s2 * sig1) + (s1 * sig2) * (s1 * sig2)) / (drop * drop)
                val after = before + record.amount
                Estimate(after, sigmaBefore / after, "water back-calculation")
            }
        }
    }
}

/** Inverse-variance combination of independent estimates. */
object Fusion {
    fun combine(estimates: List<Estimate>): Estimate? {
        val usable = estimates.filter { it.valueMl > 0 && it.relSigma > 0 }
        if (usable.isEmpty()) return null
        if (usable.size == 1) return usable[0]
        var wSum = 0.0
        var vSum = 0.0
        for (e in usable) {
            val w = 1.0 / (e.sigmaMl * e.sigmaMl)
            wSum += w
            vSum += w * e.valueMl
        }
        val value = vSum / wSum
        val sigma = sqrt(1.0 / wSum)
        return Estimate(value, sigma / value, usable.joinToString(" + ") { it.source })
    }
}

/**
 * Per-food learning (method D → A/B/C): ratio q = back-calculated broth / camera+ToF
 * estimate, averaged in log space with inverse-variance weights. Applying q corrects
 * systematic errors (γ, absorption, evaporation, registration) for that food.
 */
@Serializable
data class FoodCorrection(
    val food: String,
    val count: Int = 0,
    val weightSum: Double = 0.0,
    val weightedLogSum: Double = 0.0,
    val weightedLogSqSum: Double = 0.0,
) {
    val factor: Double get() = if (weightSum > 0) exp(weightedLogSum / weightSum) else 1.0

    /** Relative spread of the observed ratios (0 until there are two observations). */
    val relSpread: Double
        get() {
            if (count < 2 || weightSum <= 0) return 0.0
            val mean = weightedLogSum / weightSum
            val variance = (weightedLogSqSum / weightSum - mean * mean).coerceAtLeast(0.0)
            return sqrt(variance)
        }

    fun observe(backCalc: Estimate, cameraTof: Estimate): FoodCorrection {
        val q = backCalc.valueMl / cameraTof.valueMl
        if (q <= 0.2 || q >= 5.0) return this  // implausible: a wrong addition entry
        val sigma = sqrt(backCalc.relSigma * backCalc.relSigma + 0.05 * 0.05)
        val w = 1.0 / (sigma * sigma)
        val l = ln(q)
        return copy(
            count = count + 1,
            weightSum = weightSum + w,
            weightedLogSum = weightedLogSum + w * l,
            weightedLogSqSum = weightedLogSqSum + w * l * l,
        )
    }
}

enum class SolidsSource { NONE, DISPLACEMENT, DEPTH_MAP, AREA, TOF_PROTRUSION }

data class VolumePlan(
    val totalMl: Double?,
    val solidsMl: Double?,
    val solidsSource: SolidsSource,
    /** Camera + ToF broth estimate after the per-food correction. */
    val cameraTof: Estimate?,
    /** Same before the correction; learning compares back-calculations with this one. */
    val cameraTofRaw: Estimate?,
    /** Back-calculated broth volume (latest addition, carried forward), if any. */
    val backCalc: Estimate?,
    /** What the guide uses. */
    val final: Estimate?,
    /** Share of the computed amount to add first (split addition). */
    val firstStepRatio: Double,
    val notes: List<String>,
)

/** Combines methods A–D into the broth volume used by the guide. */
object VolumePlanner {
    /**
     * @param total            Vtotal from the ToF + container (calibrated profile when learned, A)
     * @param calibratedContainer whether [total] comes from a learned profile
     * @param displacementMl   solids from the ledger (B), null if not recorded this session
     * @param depthSolidsMl    solids above the surface × γ from the depth map (C)
     * @param areaSolidsMl     α·Vtotal·γ (image area method)
     * @param tofSolidsMl      8×8 protrusion × γ
     * @param correction       learned per-food factor (D)
     * @param backCalc         latest back-calculated broth (D) brought to the current state
     */
    fun plan(
        total: Double?,
        calibratedContainer: Boolean,
        displacementMl: Double?,
        depthSolidsMl: Double?,
        areaSolidsMl: Double?,
        tofSolidsMl: Double?,
        correction: FoodCorrection?,
        backCalc: Estimate?,
    ): VolumePlan {
        val notes = mutableListOf<String>()
        val (solids, source) = when {
            displacementMl != null -> displacementMl to SolidsSource.DISPLACEMENT
            depthSolidsMl != null -> depthSolidsMl to SolidsSource.DEPTH_MAP
            areaSolidsMl != null || tofSolidsMl != null ->
                listOfNotNull(areaSolidsMl, tofSolidsMl).max() to
                    (if ((areaSolidsMl ?: -1.0) >= (tofSolidsMl ?: -1.0)) SolidsSource.AREA else SolidsSource.TOF_PROTRUSION)
            else -> 0.0 to SolidsSource.NONE
        }
        var cameraTof: Estimate? = null
        var cameraTofRaw: Estimate? = null
        if (total != null && total > 0) {
            val raw = (total - solids).coerceAtLeast(total * 0.05)
            val factor = correction?.factor ?: 1.0
            // Heuristic uncertainty: container model, plus half of the solids correction
            // (B/C measure solids better than the area guess), shrunk by learning.
            val base = if (calibratedContainer) 0.05 else 0.12
            val solidsShare = solids / total
            val solidsUnc = when (source) {
                SolidsSource.DISPLACEMENT -> 0.25
                SolidsSource.DEPTH_MAP -> 0.35
                else -> 0.6
            } * solidsShare
            var rel = sqrt(base * base + solidsUnc * solidsUnc)
            cameraTofRaw = Estimate(raw, rel, "camera+ToF (uncorrected)")
            if (correction != null && correction.count >= 3) {
                rel = sqrt((rel * 0.5) * (rel * 0.5) + correction.relSpread * correction.relSpread)
                notes += "learned correction ×%.2f (%d sessions)".format(factor, correction.count)
            }
            cameraTof = Estimate(raw * factor, rel, "camera+ToF")
        } else {
            notes += "no total volume (floor / container / ToF)"
        }
        val final = Fusion.combine(listOfNotNull(cameraTof, backCalc))
        // Split addition: without a back-calculation, add only part of the amount first
        // so an over-estimated volume cannot over-salt the food.
        val ratio = when {
            backCalc != null -> 1.0
            cameraTof == null -> 0.5
            else -> (1.0 - 1.5 * cameraTof.relSigma).coerceIn(0.5, 1.0)
        }
        return VolumePlan(total, solids, source, cameraTof, cameraTofRaw, backCalc, final, ratio, notes)
    }
}
