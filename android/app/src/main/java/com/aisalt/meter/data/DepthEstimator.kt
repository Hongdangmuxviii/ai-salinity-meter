package com.aisalt.meter.data

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import android.graphics.Bitmap
import com.aisalt.meter.analysis.RelativeDepth
import java.io.Closeable
import java.io.File
import java.nio.FloatBuffer

/**
 * Monocular relative-depth model run with ONNX Runtime (method C).
 * Intended models: Depth Anything V2 Small (Apache-2.0) or MiDaS v2.1 small (MIT),
 * exported to ONNX with input [1,3,H,W] (ImageNet-normalised RGB) and output
 * [1,H,W] or [1,1,H,W] relative inverse depth. The model file is imported by the
 * user into app storage; it is not bundled in the APK.
 */
class DepthEstimator(private val modelFile: File, private val fallbackSize: Int = 518) : Closeable {
    private val env: OrtEnvironment = OrtEnvironment.getEnvironment()
    private val session: OrtSession = env.createSession(modelFile.absolutePath, OrtSession.SessionOptions())
    private val inputName: String = session.inputNames.first()
    /** Fixed model input size, or null when height/width are dynamic. */
    private val fixedSize: Pair<Int, Int>?

    init {
        val shape = (session.inputInfo[inputName]?.info as? TensorInfo)?.shape
        val h = shape?.getOrNull(2)?.takeIf { it > 0 }?.toInt()
        val w = shape?.getOrNull(3)?.takeIf { it > 0 }?.toInt()
        fixedSize = if (h != null && w != null) w to h else null
    }

    val description: String
        get() = "${modelFile.name} (" + (fixedSize?.let { "${it.first}×${it.second}" } ?: "짧은 변 $fallbackSize, 비율 유지") + ")"

    /**
     * Dynamic-size models (Depth Anything ONNX) are fed like their DPT preprocessor:
     * shorter side [fallbackSize], aspect ratio kept, both sides multiples of 14.
     */
    private fun inputSizeFor(bitmap: Bitmap): Pair<Int, Int> {
        fixedSize?.let { return it }
        fun mult14(v: Double) = maxOf(14, (Math.round(v / 14.0) * 14).toInt())
        val aspect = bitmap.width.toDouble() / bitmap.height
        return if (aspect >= 1.0) mult14(fallbackSize * aspect) to fallbackSize
        else fallbackSize to mult14(fallbackSize / aspect)
    }

    fun estimate(bitmap: Bitmap): RelativeDepth {
        val (w, h) = inputSizeFor(bitmap)
        val scaled = Bitmap.createScaledBitmap(bitmap, w, h, true)
        val pixels = IntArray(w * h)
        scaled.getPixels(pixels, 0, w, 0, 0, w, h)
        val mean = floatArrayOf(0.485f, 0.456f, 0.406f)
        val std = floatArrayOf(0.229f, 0.224f, 0.225f)
        val input = FloatArray(3 * w * h)
        val plane = w * h
        for (i in 0 until plane) {
            val p = pixels[i]
            input[i] = (((p shr 16) and 0xFF) / 255f - mean[0]) / std[0]
            input[plane + i] = (((p shr 8) and 0xFF) / 255f - mean[1]) / std[1]
            input[2 * plane + i] = ((p and 0xFF) / 255f - mean[2]) / std[2]
        }
        OnnxTensor.createTensor(env, FloatBuffer.wrap(input), longArrayOf(1, 3, h.toLong(), w.toLong())).use { tensor ->
            session.run(mapOf(inputName to tensor)).use { result ->
                val out = result[0] as OnnxTensor
                val shape = out.info.shape
                val outH = shape[shape.size - 2].toInt()
                val outW = shape[shape.size - 1].toInt()
                val buffer = out.floatBuffer
                val values = FloatArray(outW * outH)
                buffer.get(values)
                return RelativeDepth(outW, outH, values, isInverse = true)
            }
        }
    }

    override fun close() {
        session.close()
    }

    companion object {
        fun modelFile(filesDir: File) = File(filesDir, "depth/model.onnx")
    }
}
