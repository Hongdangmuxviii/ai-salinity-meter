package com.aisalt.meter.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import java.util.Locale

fun fmt(v: Double?, digits: Int = 1, unit: String = ""): String =
    if (v == null || v.isNaN()) "—" else String.format(Locale.US, "%.${digits}f", v) + unit

@Composable
fun Section(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
fun KeyValue(key: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(key, style = MaterialTheme.typography.bodyMedium)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
    }
}

/** Decimal input that commits only parseable values. */
@Composable
fun NumberField(
    label: String,
    value: Double?,
    modifier: Modifier = Modifier,
    digits: Int = 2,
    onCommit: (Double?) -> Unit,
) {
    var text by remember { mutableStateOf(value?.let { fmt(it, digits) } ?: "") }
    LaunchedEffect(value) {
        val parsed = text.toDoubleOrNull()
        if (parsed != value) text = value?.let { fmt(it, digits) } ?: ""
    }
    OutlinedTextField(
        value = text,
        onValueChange = { t ->
            text = t
            if (t.isBlank()) onCommit(null) else t.toDoubleOrNull()?.let(onCommit)
        },
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        modifier = modifier,
    )
}
