package com.aisalt.meter.protocol

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull

/** Events sent by SalinityMeterApp firmware (firmware/SalinityMeterApp/README.md §4). */
sealed interface DeviceEvent {
    data class Hello(
        val fw: String?, val name: String?, val cal: String?,
        val adc: Boolean, val tempSensor: Boolean, val oled: Boolean,
        val tof: Boolean, val camera: Boolean, val psram: Boolean,
        val timeSet: Boolean, val records: Int?,
    ) : DeviceEvent

    data class Salinity(
        val seq: Long?, val pct: Double?, val tablePct: Double?, val index: Double?,
        val tempC: Double?, val span: String?, val unstable: Boolean,
        val trials: List<Double?>, val temperatureCompensated: Boolean, val epoch: Long?,
    ) : DeviceEvent

    data class Tof(
        val surfaceMm: Double?, val spreadMm: Double?, val validZones: Int?,
        val floorMm: Double?, val fillMm: Double?, val totalMl: Double?,
        val brothMl: Double?, val note: String?, val grid: IntArray,
    ) : DeviceEvent

    data class DeviceGuide(
        val targetPct: Double?, val currentPct: Double?, val kind: String?,
        val amount: Double?, val unit: String?, val perLiter: Boolean,
        val brothMl: Double?, val round: Int?, val reached: Boolean, val advise: Boolean,
    ) : DeviceEvent

    data class ImageBegin(
        val id: Int, val bytes: Int, val crc32: Long, val width: Int?, val height: Int?,
        val chunkBytes: Int, val chunks: Int,
    ) : DeviceEvent

    data class ImageEnd(val id: Int, val sent: Int?, val requested: Int?, val complete: Boolean) : DeviceEvent

    data class Settings(val values: JsonObject) : DeviceEvent {
        fun double(key: String) = values[key]?.jsonPrimitive?.doubleOrNull
        fun string(key: String) = values[key]?.jsonPrimitive?.contentOrNull
    }

    data class Record(
        val seq: Long?, val epoch: Long?, val pct: Double?, val tempC: Double?,
        val brothMl: Double?, val targetPct: Double?, val span: String?,
    ) : DeviceEvent

    data class HistoryEnd(val count: Int?) : DeviceEvent
    data class Raw(val index: Double?, val tempC: Double?) : DeviceEvent
    data class Temp(val tempC: Double?) : DeviceEvent
    data class Ack(val cmd: String?) : DeviceEvent
    data class Error(val op: String?, val code: String?, val msg: String?) : DeviceEvent
    data class Unknown(val type: String?, val line: String) : DeviceEvent

    companion object {
        private val json = Json { ignoreUnknownKeys = true }

        fun parse(line: String): DeviceEvent {
            val obj = try {
                json.parseToJsonElement(line).jsonObject
            } catch (e: Exception) {
                return Unknown(null, line)
            }
            val type = obj.str("type")
            return when (type) {
                "hello" -> Hello(
                    obj.str("fw"), obj.str("name"), obj.str("cal"),
                    obj.bool("adc"), obj.bool("tempSensor"), obj.bool("oled"),
                    obj.bool("tof"), obj.bool("camera"), obj.bool("psram"),
                    obj.bool("timeSet"), obj.int("records"),
                )
                "salinity" -> Salinity(
                    obj.long("seq"), obj.dbl("pct"), obj.dbl("tablePct"), obj.dbl("index"),
                    obj.dbl("tempC"), obj.str("span"), obj.bool("unstable"),
                    (obj["trials"] as? JsonArray)?.map { (it as? JsonPrimitive)?.doubleOrNull } ?: emptyList(),
                    obj.bool("temperatureCompensated"), obj.long("epoch"),
                )
                "tof" -> Tof(
                    obj.dbl("surfaceMm"), obj.dbl("spreadMm"), obj.int("validZones"),
                    obj.dbl("floorMm"), obj.dbl("fillMm"), obj.dbl("totalMl"),
                    obj.dbl("brothMl"), obj.str("note"),
                    (obj["grid"] as? JsonArray)?.map { (it as? JsonPrimitive)?.intOrNull ?: -1 }?.toIntArray()
                        ?: IntArray(0),
                )
                "guide" -> DeviceGuide(
                    obj.dbl("targetPct"), obj.dbl("currentPct"), obj.str("kind"),
                    obj.dbl("amount"), obj.str("unit"), obj.bool("perLiter"),
                    obj.dbl("brothMl"), obj.int("round"), obj.bool("reached"), obj.bool("advise"),
                )
                "image_begin" -> ImageBegin(
                    obj.int("id") ?: 0, obj.int("bytes") ?: 0,
                    obj.str("crc32")?.toLongOrNull(16) ?: -1L,
                    obj.int("width"), obj.int("height"),
                    obj.int("chunkBytes") ?: 0, obj.int("chunks") ?: 0,
                )
                "image_end" -> ImageEnd(obj.int("id") ?: 0, obj.int("sent"), obj.int("requested"), obj.bool("complete"))
                "settings" -> Settings(obj)
                "record" -> Record(
                    obj.long("seq"), obj.long("epoch"), obj.dbl("pct"), obj.dbl("tempC"),
                    obj.dbl("brothMl"), obj.dbl("targetPct"), obj.str("span"),
                )
                "history_end" -> HistoryEnd(obj.int("count"))
                "raw" -> Raw(obj.dbl("index"), obj.dbl("tempC"))
                "temp" -> Temp(obj.dbl("tempC"))
                "ack" -> Ack(obj.str("cmd"))
                "error" -> Error(obj.str("op"), obj.str("code"), obj.str("msg"))
                else -> Unknown(type, line)
            }
        }

        private fun JsonObject.prim(key: String) = this[key] as? JsonPrimitive
        private fun JsonObject.str(key: String) = prim(key)?.contentOrNull
        private fun JsonObject.dbl(key: String) = prim(key)?.doubleOrNull
        private fun JsonObject.int(key: String) = prim(key)?.intOrNull
        private fun JsonObject.long(key: String) = prim(key)?.longOrNull
        private fun JsonObject.bool(key: String) = prim(key)?.booleanOrNull ?: false
    }
}
