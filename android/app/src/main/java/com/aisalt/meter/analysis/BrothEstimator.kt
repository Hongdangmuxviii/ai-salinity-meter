package com.aisalt.meter.analysis

/**
 * How the solids volume is derived (patent ¶77-¶79).
 *  - AREA:       Vsolid = α · Vtotal · γarea                      (¶78)
 *  - PROTRUSION: Vsolid = Σ (Dsurface − d_i) · A_i · γprotrusion  (¶77, depth map over solid zones)
 *  - MAX:        larger of the two (conservative: less salt is suggested)
 *  - NONE:       no solids correction
 * The γ values are per-food coefficients the patent leaves to experiments; the
 * defaults are placeholders until they are measured.
 */
enum class SolidsMethod { NONE, AREA, PROTRUSION, MAX }

data class SolidsModel(
    val method: SolidsMethod = SolidsMethod.MAX,
    /** Fraction of the solids' column that is solid (area method). Provisional. */
    val gammaArea: Double = 0.5,
    /** Total solid volume / part above the surface (protrusion method). Provisional. */
    val gammaProtrusion: Double = 2.0,
    /** Height above the surface that counts as protrusion (ToF noise). */
    val protrusionMarginMm: Double = 4.0,
    /** Zone counts as "solid" for protrusion when this share of its pixels is solid. */
    val solidZoneFraction: Double = 0.5,
    /** Zone counts as clean broth surface below this share of solid pixels. */
    val brothZoneMaxSolid: Double = 0.2,
)

data class BrothInputs(
    /** 64 distances (mm) row-major, -1 = invalid zone (device `tof.grid`). */
    val tofGrid: IntArray,
    /** Empty-container distance to the floor (Dfloor), mm. */
    val floorMm: Double?,
    val container: Container,
    val segmentation: Segmentation?,
    val registration: Registration = Registration(),
    val tof: TofGeometry = TofGeometry(),
    val solids: SolidsModel = SolidsModel(),
)

data class BrothEstimate(
    val surfaceMm: Double?,
    val fillMm: Double?,
    val totalMl: Double?,
    val alpha: Double?,
    val solidsAreaMl: Double?,
    val solidsProtrusionMl: Double?,
    val solidsMl: Double?,
    val brothMl: Double?,
    val brothZones: Int,
    val solidZones: Int,
    val notes: List<String>,
) {
    /** Vsolid / Vtotal, sent to the device as `solids <ratio> 1` so its OLED guide matches. */
    val effectiveSolidsRatio: Double?
        get() = if (totalMl != null && totalMl > 0 && solidsMl != null) solidsMl / totalMl else null
}

/** Patent S400: surface height from the depth map + container shape - solids. */
object BrothEstimator {

    fun estimate(input: BrothInputs): BrothEstimate {
        val notes = mutableListOf<String>()
        val n = input.tof.zonesPerSide
        require(input.tofGrid.size == n * n) { "grid must have ${n * n} zones" }
        val seg = input.segmentation

        // 1. Classify zones by their image footprint.
        val solidShare = DoubleArray(n * n) { Double.NaN }
        if (seg != null) {
            for (row in 0 until n) for (col in 0 until n) {
                val rect = input.registration.zoneRect(row, col, input.tof)
                solidShare[row * n + col] = seg.solidFraction(rect) ?: Double.NaN
            }
        }
        val valid = { i: Int -> input.tofGrid[i] > 0 }
        val inBowl = { i: Int -> seg == null || !solidShare[i].isNaN() }

        // 2. Surface distance: median of clean broth zones (patent ¶69 statistics).
        val brothZones = (0 until n * n).filter {
            valid(it) && inBowl(it) && (seg == null || solidShare[it] <= input.solids.brothZoneMaxSolid)
        }
        val center = (0 until n * n).filter {
            val r = it / n
            val c = it % n
            valid(it) && r in 2..5 && c in 2..5
        }
        // Without an image the bowl outline is unknown, so only the centre 4×4 zones
        // are trusted (outer zones may see the rim or the table).
        val surfaceSource = when {
            seg != null && brothZones.size >= 3 -> brothZones
            center.size >= 4 -> {
                if (seg != null) notes += "few clean broth zones; using centre zones"
                center
            }
            else -> emptyList()
        }
        val surface = surfaceSource.map { input.tofGrid[it].toDouble() }.medianOrNull()
        if (surface == null) notes += "not enough valid ToF zones"

        // 3. Fill height and total volume.
        val floor = input.floorMm
        var fill: Double? = null
        var total: Double? = null
        if (floor == null) {
            notes += "floor reference (empty container) not set"
        } else if (surface != null) {
            val h = floor - surface
            when {
                h < -3.0 -> notes += "surface farther than the floor reference"
                h > input.container.depthMm * 1.1 -> notes += "fill exceeds container depth"
                else -> {
                    fill = h.coerceIn(0.0, input.container.depthMm)
                    total = input.container.volumeMl(fill)
                }
            }
        }

        // 4. Solids volume.
        val alpha = seg?.alpha
        val solidZones = (0 until n * n).filter {
            valid(it) && !solidShare[it].isNaN() && solidShare[it] >= input.solids.solidZoneFraction
        }
        val areaMl = if (total != null && alpha != null) alpha * total * input.solids.gammaArea else null
        val protrusionMl = if (surface != null && seg != null) {
            var mm3 = 0.0
            for (i in solidZones) {
                val d = input.tofGrid[i].toDouble()
                val p = surface - d - input.solids.protrusionMarginMm
                if (p > 0) mm3 += p * input.tof.zoneAreaMm2(d) * solidShare[i]
            }
            mm3 / 1000.0 * input.solids.gammaProtrusion
        } else null
        if (seg == null) notes += "no image: solids not corrected"

        val solids = when (input.solids.method) {
            SolidsMethod.NONE -> 0.0
            SolidsMethod.AREA -> areaMl
            SolidsMethod.PROTRUSION -> protrusionMl
            SolidsMethod.MAX -> listOfNotNull(areaMl, protrusionMl).maxOrNull()
        }
        val broth = when {
            total == null -> null
            solids == null -> total
            else -> (total - solids).coerceAtLeast(0.0)
        }
        return BrothEstimate(
            surfaceMm = surface,
            fillMm = fill,
            totalMl = total,
            alpha = alpha,
            solidsAreaMl = areaMl,
            solidsProtrusionMl = protrusionMl,
            solidsMl = if (total == null) null else solids ?: 0.0,
            brothMl = broth,
            brothZones = surfaceSource.size,
            solidZones = solidZones.size,
            notes = notes,
        )
    }

    private fun List<Double>.medianOrNull(): Double? {
        if (isEmpty()) return null
        val s = sorted()
        return if (s.size % 2 == 1) s[s.size / 2] else (s[s.size / 2 - 1] + s[s.size / 2]) / 2.0
    }
}
