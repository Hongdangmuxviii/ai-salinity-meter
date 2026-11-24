package com.aisalt.meter.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.data.MeterUiState
import com.aisalt.meter.data.MeterViewModel

/** Raw protocol view: every JSON line and a free-form command box (firmware README §4). */
@Composable
fun LogScreen(st: MeterUiState, vm: MeterViewModel, modifier: Modifier) {
    var command by remember { mutableStateOf("") }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = command,
                onValueChange = { command = it },
                label = { Text("명령 (예: settings, history, cellcal 1.0)") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            Button(
                onClick = { vm.send(command); command = "" },
                enabled = st.link == LinkState.READY && command.isNotBlank(),
            ) { Text("전송") }
        }
        LazyColumn(Modifier.fillMaxWidth(), reverseLayout = true) {
            items(st.log.asReversed()) { line ->
                Text(line, fontFamily = FontFamily.Monospace, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
