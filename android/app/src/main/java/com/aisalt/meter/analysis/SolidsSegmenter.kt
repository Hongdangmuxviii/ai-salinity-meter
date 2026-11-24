package com.aisalt.meter.analysis

import kotlin.math.cbrt
import kotlin.math.pow
import kotlin.math.sqrt

/** Packed ARGB pixels (Android Bitmap.getPixels layout), independent of Android. */
class RgbImage(val width: Int, val height: Int, val argb: IntArray) {
    init {
        require(argb.size == width * height) { "pixel count mismatch" }
    }
}

/** Container opening in the image: centre and radius normalised to min(width, height). */
data class BowlCircle(val cx: Double = 0.5, val cy: Double = 0.5, val r: Double = 0.42)

data class Lab(val l: Double, val a: Double, val b: Double) {
    fun deltaE(o: Lab): Double {
        val dl = l - o.l
        val da = a - o.a
        val db = b - o.b
        return sqrt(dl * dl + da * da + db * db)
    }

    companion object {
        /** sRGB (D65) -> CIELAB. */
        fun fromArgb(argb: Int): Lab {
            fun lin(c: Int): Double {
                val v = c / 255.0
                return if (v <= 0.04045) v / 12.92 else ((v + 0.055) / 1.055).pow(2.4)
            }
            val r = lin((argb shr 16) and 0xFF)
            val g = lin((argb shr 8) and 0xFF)
            val b = lin(argb and 0xFF)
            val x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
            val y = 0.2126 * r + 0.7152 * g + 0.0722 * b
            val z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
            fun f(t: Double) = if (t > 0.008856) cbrt(t) else 7.787 * t + 16.0 / 116.0
            val fx = f(x)
            val fy = f(y)
            val fz = f(z)
            return Lab(116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))
        }
    }
}

/**
 * Per-pixel labels inside the container opening.
 * [labels]: 0 = outside / ignored rim, 1 = broth, 2 = solid, 3 = glare (excluded).
 */
class Segmentation(
    val width: Int,
    val height: Int,
    val labels: ByteArray,
    val brothColor: Lab,
    val brothPixels: Int,
    val solidPixels: Int,
    val glarePixels: Int,
    val method: String,
) {
    /** Patent ¶78 α: solid area / (broth + solid) area. */
    val alpha: Double get() = if (brothPixels + solidPixels == 0) 0.0 else solidPixels.toDouble() / (brothPixels + solidPixels)

    /** Solid fraction inside [rect]; null when the rect has no broth/solid pixels. */
    fun solidFraction(rect: NormRect): Double? {
        if (rect.isEmpty) return null
        val x0 = (rect.left * width).toInt().coerceIn(0, width)
        val x1 = (rect.right * width).toInt().coerceIn(0, width)
        val y0 = (rect.top * height).toInt().coerceIn(0, height)
        val y1 = (rect.bottom * height).toInt().coerceIn(0, height)
        var solid = 0
        var counted = 0
        for (y in y0 until y1) for (x in x0 until x1) {
            when (labels[y * width + x].toInt()) {
                1 -> counted++
                2 -> { counted++; solid++ }
            }
        }
        return if (counted == 0) null else solid.toDouble() / counted
    }

    companion object {
        const val OUTSIDE: Byte = 0
        const val BROTH: Byte = 1
        const val SOLID: Byte = 2
        const val GLARE: Byte = 3
    }
}

/** Solids detection step (patent ¶74-¶75). Swappable for a trained segmentation model. */
fun interface SolidsSegmenter {
    fun segment(image: RgbImage, bowl: BowlCircle): Segmentation
}

/**
 * MVP classical segmenter (patent ¶75 "colour distribution ... conventional image
 * processing"). Assumes broth covers most of the opening: the broth colour is the
 * per-channel median in CIELAB, and pixels further than [deltaEThreshold] from it
 * are solids. Specular glare is excluded from both. A 3×3 majority pass removes
 * speckle. Thresholds are starting values to be tuned with real food photos.
 */
class ColorSolidsSegmenter(
    private val deltaEThreshold: Double = 18.0,
    private val innerMargin: Double = 0.9,
    private val glareLightness: Double = 92.0,
    private val glareChroma: Double = 8.0,
) : SolidsSegmenter {

    override fun segment(image: RgbImage, bowl: BowlCircle): Segmentation {
        val w = image.width
        val h = image.height
        val scale = minOf(w, h).toDouble()
        val cx = bowl.cx * w
        val cy = bowl.cy * h
        val radius = bowl.r * scale * innerMargin
        val r2 = radius * radius
        val labs = arrayOfNulls<Lab>(w * h)
        val labels = ByteArray(w * h)

        val ls = ArrayList<Double>()
        val aas = ArrayList<Double>()
        val bs = ArrayList<Double>()
        for (y in 0 until h) for (x in 0 until w) {
            val dx = x + 0.5 - cx
            val dy = y + 0.5 - cy
            if (dx * dx + dy * dy > r2) continue
            val i = y * w + x
            val lab = Lab.fromArgb(image.argb[i])
            labs[i] = lab
            val chroma = sqrt(lab.a * lab.a + lab.b * lab.b)
            if (lab.l >= glareLightness && chroma <= glareChroma) {
                labels[i] = Segmentation.GLARE
            } else {
                labels[i] = Segmentation.BROTH
                ls += lab.l
                aas += lab.a
                bs += lab.b
            }
        }
        if (ls.isEmpty()) {
            return Segmentation(w, h, labels, Lab(0.0, 0.0, 0.0), 0, 0, 0, "color-deltaE")
        }
        val broth = Lab(median(ls), median(aas), median(bs))
        for (i in labels.indices) {
            if (labels[i] == Segmentation.BROTH && labs[i]!!.deltaE(broth) > deltaEThreshold) {
                labels[i] = Segmentation.SOLID
            }
        }
        val cleaned = majority(labels, w, h)
        var brothCount = 0
        var solidCount = 0
        var glareCount = 0
        for (v in cleaned) when (v) {
            Segmentation.BROTH -> brothCount++
            Segmentation.SOLID -> solidCount++
            Segmentation.GLARE -> glareCount++
        }
        return Segmentation(w, h, cleaned, broth, brothCount, solidCount, glareCount, "color-deltaE")
    }

    private fun median(values: ArrayList<Double>): Double {
        values.sort()
        return values[values.size / 2]
    }

    /** Broth/solid pixels take the majority label of their 3×3 neighbourhood. */
    private fun majority(src: ByteArray, w: Int, h: Int): ByteArray {
        val out = src.copyOf()
        for (y in 1 until h - 1) for (x in 1 until w - 1) {
            val i = y * w + x
            if (src[i] != Segmentation.BROTH && src[i] != Segmentation.SOLID) continue
            var solid = 0
            var broth = 0
            for (dy in -1..1) for (dx in -1..1) {
                when (src[(y + dy) * w + x + dx]) {
                    Segmentation.SOLID -> solid++
                    Segmentation.BROTH -> broth++
                }
            }
            if (solid > broth && solid >= 5) out[i] = Segmentation.SOLID
            else if (broth > solid && broth >= 5) out[i] = Segmentation.BROTH
        }
        return out
    }
}
