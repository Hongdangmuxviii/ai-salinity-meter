package com.aisalt.meter.protocol

import com.aisalt.meter.analysis.Container
import java.util.Locale

/** Text commands written to the NUS RX characteristic (firmware README §4). */
object Commands {
    private fun f(v: Double, digits: Int = 2) = String.format(Locale.US, "%.${digits}f", v)

    const val MEASURE = "measure"
    const val RECHECK = "recheck"
    const val TOF = "tof"
    const val STATUS = "status"
    const val SETTINGS = "settings"
    const val HISTORY = "history"
    const val SAVE = "save"
    const val FLOOR_FROM_TOF = "floor"
    const val FLOOR_CLEAR = "floor clear"

    fun scan(size: String = "vga") = "scan $size"
    fun photo(size: String = "vga") = "photo $size"
    fun target(pct: Double) = "target ${f(pct)}"
    fun floor(mm: Double) = "floor ${f(mm, 1)}"
    fun time(epochSeconds: Long) = "time $epochSeconds"

    /** Effective solids ratio Vsolid/Vtotal with γ = 1, so the device guide matches the app. */
    fun solids(ratio: Double) = "solids ${f(ratio.coerceIn(0.0, 0.95), 3)} 1"

    fun bowl(container: Container): String? = when (container) {
        is Container.Round -> "bowl round ${f(container.topDiameterMm, 1)} ${f(container.bottomDiameterMm, 1)} ${f(container.depthMm, 1)}"
        is Container.Rect -> "bowl rect ${f(container.widthMm, 1)} ${f(container.lengthMm, 1)} ${f(container.depthMm, 1)}"
        // Device only models round / rect; learned shapes are sent as a broth volume instead.
        is Container.Profile, is Container.Calibrated -> null
    }

    /**
     * App-computed broth volume for the device's OLED guide (firmware `broth` command),
     * with the share of the amount to show for the first (split) addition.
     */
    fun broth(ml: Double, firstStepRatio: Double) =
        "broth ${f(ml, 0)} ${f(firstStepRatio.coerceIn(0.1, 1.0), 2)}"

    const val BROTH_CLEAR = "broth clear"

    /** Resend specific chunks; the firmware accepts up to 10 indices per command. */
    fun resendChunks(id: Int, chunks: List<Int>): List<String> =
        chunks.chunked(10).map { group -> "img $id ${group.joinToString(" ")}" }
}
