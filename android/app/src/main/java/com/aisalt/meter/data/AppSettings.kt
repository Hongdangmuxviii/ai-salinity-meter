package com.aisalt.meter.data

import android.content.Context
import com.aisalt.meter.analysis.BowlCircle
import com.aisalt.meter.analysis.Container
import com.aisalt.meter.analysis.Registration
import com.aisalt.meter.analysis.SaltGuide
import com.aisalt.meter.analysis.SolidsMethod
import com.aisalt.meter.analysis.SolidsModel

enum class ContainerShape { ROUND, RECT }

/** User / calibration settings kept on the phone. */
data class AppSettings(
    val targetPct: Double = 0.8,
    val shape: ContainerShape = ContainerShape.ROUND,
    /** Round: top Ø, bottom Ø. Rect: width, length. */
    val dimAMm: Double = 86.0,
    val dimBMm: Double = 66.0,
    val depthMm: Double = 88.0,
    /** Dfloor; null = not set (taken from the device `settings.floorMm` when available). */
    val floorMm: Double? = null,
    val solids: SolidsModel = SolidsModel(),
    val deltaEThreshold: Double = 18.0,
    val bowl: BowlCircle = BowlCircle(),
    val registration: Registration = Registration(),
    val saltK: Double = SaltGuide.K_DEFAULT,
    val photoSize: String = "vga",
) {
    val container: Container
        get() = when (shape) {
            ContainerShape.ROUND -> Container.Round(dimAMm, dimBMm, depthMm)
            ContainerShape.RECT -> Container.Rect(dimAMm, dimBMm, depthMm)
        }
}

class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("salt_meter", Context.MODE_PRIVATE)

    fun load(): AppSettings {
        val d = AppSettings()
        fun dbl(key: String, def: Double) =
            if (prefs.contains(key)) java.lang.Double.longBitsToDouble(prefs.getLong(key, 0)) else def
        return AppSettings(
            targetPct = dbl("target", d.targetPct),
            shape = runCatching { ContainerShape.valueOf(prefs.getString("shape", d.shape.name)!!) }.getOrDefault(d.shape),
            dimAMm = dbl("dimA", d.dimAMm),
            dimBMm = dbl("dimB", d.dimBMm),
            depthMm = dbl("depth", d.depthMm),
            floorMm = if (prefs.contains("floor")) dbl("floor", 0.0) else null,
            solids = SolidsModel(
                method = runCatching { SolidsMethod.valueOf(prefs.getString("solidsMethod", d.solids.method.name)!!) }
                    .getOrDefault(d.solids.method),
                gammaArea = dbl("gammaArea", d.solids.gammaArea),
                gammaProtrusion = dbl("gammaProtrusion", d.solids.gammaProtrusion),
            ),
            deltaEThreshold = dbl("deltaE", d.deltaEThreshold),
            bowl = BowlCircle(dbl("bowlCx", d.bowl.cx), dbl("bowlCy", d.bowl.cy), dbl("bowlR", d.bowl.r)),
            registration = Registration(
                cameraHFovDeg = dbl("camH", d.registration.cameraHFovDeg),
                cameraVFovDeg = dbl("camV", d.registration.cameraVFovDeg),
                rotateQuarterTurns = prefs.getInt("tofRot", d.registration.rotateQuarterTurns),
                mirrorX = prefs.getBoolean("tofMirror", d.registration.mirrorX),
            ),
            saltK = dbl("saltK", d.saltK),
            photoSize = prefs.getString("photoSize", d.photoSize) ?: d.photoSize,
        )
    }

    fun save(s: AppSettings) {
        val e = prefs.edit()
        fun put(key: String, v: Double) = e.putLong(key, java.lang.Double.doubleToRawLongBits(v))
        put("target", s.targetPct)
        e.putString("shape", s.shape.name)
        put("dimA", s.dimAMm)
        put("dimB", s.dimBMm)
        put("depth", s.depthMm)
        if (s.floorMm != null) put("floor", s.floorMm) else e.remove("floor")
        e.putString("solidsMethod", s.solids.method.name)
        put("gammaArea", s.solids.gammaArea)
        put("gammaProtrusion", s.solids.gammaProtrusion)
        put("deltaE", s.deltaEThreshold)
        put("bowlCx", s.bowl.cx)
        put("bowlCy", s.bowl.cy)
        put("bowlR", s.bowl.r)
        put("camH", s.registration.cameraHFovDeg)
        put("camV", s.registration.cameraVFovDeg)
        e.putInt("tofRot", s.registration.rotateQuarterTurns)
        e.putBoolean("tofMirror", s.registration.mirrorX)
        put("saltK", s.saltK)
        e.putString("photoSize", s.photoSize)
        e.apply()
    }
}
