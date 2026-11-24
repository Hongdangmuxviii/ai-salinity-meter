package com.aisalt.meter.data

import android.content.Context
import com.aisalt.meter.analysis.ContainerProfile
import com.aisalt.meter.analysis.FoodCorrection
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json

/** Learned containers (A) and per-food corrections (D), kept on the phone. */
class CookStore(context: Context) {
    private val prefs = context.getSharedPreferences("salt_meter_cook", Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true }

    fun profiles(): List<ContainerProfile> = read("profiles", ListSerializer(ContainerProfile.serializer()))

    fun saveProfile(profile: ContainerProfile) {
        val list = profiles().filterNot { it.name == profile.name } + profile
        write("profiles", ListSerializer(ContainerProfile.serializer()), list)
    }

    fun deleteProfile(name: String) {
        write("profiles", ListSerializer(ContainerProfile.serializer()), profiles().filterNot { it.name == name })
        if (activeProfile() == name) setActiveProfile(null)
    }

    fun activeProfile(): String? = prefs.getString("activeProfile", null)

    fun setActiveProfile(name: String?) {
        prefs.edit().apply { if (name == null) remove("activeProfile") else putString("activeProfile", name) }.apply()
    }

    fun corrections(): List<FoodCorrection> = read("corrections", ListSerializer(FoodCorrection.serializer()))

    fun saveCorrection(correction: FoodCorrection) {
        val list = corrections().filterNot { it.food == correction.food } + correction
        write("corrections", ListSerializer(FoodCorrection.serializer()), list)
    }

    fun foodName(): String = prefs.getString("food", "기본") ?: "기본"

    fun setFoodName(name: String) = prefs.edit().putString("food", name).apply()

    private fun <T> read(key: String, serializer: kotlinx.serialization.KSerializer<List<T>>): List<T> {
        val text = prefs.getString(key, null) ?: return emptyList()
        return runCatching { json.decodeFromString(serializer, text) }.getOrDefault(emptyList())
    }

    private fun <T> write(key: String, serializer: kotlinx.serialization.KSerializer<List<T>>, value: List<T>) {
        prefs.edit().putString(key, json.encodeToString(serializer, value)).apply()
    }
}
