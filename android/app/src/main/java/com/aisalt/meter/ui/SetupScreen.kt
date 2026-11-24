package com.aisalt.meter.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.aisalt.meter.analysis.SolidsMethod
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.data.ContainerShape
import com.aisalt.meter.data.MeterUiState
import com.aisalt.meter.data.MeterViewModel

@Composable
fun SetupScreen(st: MeterUiState, vm: MeterViewModel, modifier: Modifier) {
    val s = st.settings
    val ready = st.link == LinkState.READY
    val half = Modifier.fillMaxWidth()

    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Section("용기 (특허 ¶66, ¶71–73)") {
            Choice(
                listOf(ContainerShape.ROUND to "원형/테이퍼", ContainerShape.RECT to "사각"),
                s.shape,
            ) { shape -> vm.updateSettings { it.copy(shape = shape) } }
            val round = s.shape == ContainerShape.ROUND
            NumberField(if (round) "위 안지름 mm" else "가로 mm", s.dimAMm, half, 1) { v ->
                if (v != null && v > 0) vm.updateSettings { it.copy(dimAMm = v) }
            }
            NumberField(if (round) "바닥 안지름 mm" else "세로 mm", s.dimBMm, half, 1) { v ->
                if (v != null && v > 0) vm.updateSettings { it.copy(dimBMm = v) }
            }
            NumberField("안쪽 깊이 mm", s.depthMm, half, 1) { v ->
                if (v != null && v > 0) vm.updateSettings { it.copy(depthMm = v) }
            }
        }

        Section("바닥 기준거리 Dfloor (특허 ¶59)") {
            Text("빈 용기를 센서 아래에 두고 기기에서 측정해 저장합니다.", style = MaterialTheme.typography.bodySmall)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NumberField("Dfloor mm", s.floorMm, Modifier.weight(1f), 1) { v ->
                    vm.updateSettings { it.copy(floorMm = v) }
                }
                OutlinedButton(onClick = vm::captureFloorOnDevice, enabled = ready) { Text("빈 용기 측정") }
            }
        }

        Section("건더기 보정 (특허 ¶74–79)") {
            Choice(
                listOf(
                    SolidsMethod.MAX to "큰 값",
                    SolidsMethod.AREA to "면적식",
                    SolidsMethod.PROTRUSION to "돌출식",
                    SolidsMethod.NONE to "보정 안 함",
                ),
                s.solids.method,
            ) { m -> vm.updateSettings { it.copy(solids = it.solids.copy(method = m)) } }
            Text("γ는 음식별 실험값이 필요합니다. 기본값은 임시값입니다.", style = MaterialTheme.typography.bodySmall)
            NumberField("γ 면적식 (Vsolid = α·Vtotal·γ)", s.solids.gammaArea, half) { v ->
                if (v != null && v in 0.0..2.0) vm.updateSettings { it.copy(solids = it.solids.copy(gammaArea = v)) }
            }
            NumberField("γ 돌출식 (전체/수면 위 비율)", s.solids.gammaProtrusion, half) { v ->
                if (v != null && v in 0.0..10.0) vm.updateSettings { it.copy(solids = it.solids.copy(gammaProtrusion = v)) }
            }
            NumberField("색 차이 임계값 ΔE", s.deltaEThreshold, half, 1) { v ->
                if (v != null && v in 3.0..80.0) vm.updateSettings { it.copy(deltaEThreshold = v) }
            }
        }

        Section("사진 속 용기 입구 원") {
            Text("중심과 반지름은 사진 짧은 변 기준 비율(0~1)입니다.", style = MaterialTheme.typography.bodySmall)
            NumberField("중심 x", s.bowl.cx, half, 3) { v ->
                if (v != null && v in 0.0..1.0) vm.updateSettings { it.copy(bowl = it.bowl.copy(cx = v)) }
            }
            NumberField("중심 y", s.bowl.cy, half, 3) { v ->
                if (v != null && v in 0.0..1.0) vm.updateSettings { it.copy(bowl = it.bowl.copy(cy = v)) }
            }
            NumberField("반지름 r", s.bowl.r, half, 3) { v ->
                if (v != null && v in 0.05..1.0) vm.updateSettings { it.copy(bowl = it.bowl.copy(r = v)) }
            }
        }

        Section("카메라–ToF 정합 (특허 ¶60–61)") {
            NumberField("카메라 수평 화각 °", s.registration.cameraHFovDeg, half, 1) { v ->
                if (v != null && v in 20.0..140.0) vm.updateSettings { it.copy(registration = it.registration.copy(cameraHFovDeg = v)) }
            }
            NumberField("카메라 수직 화각 °", s.registration.cameraVFovDeg, half, 1) { v ->
                if (v != null && v in 15.0..120.0) vm.updateSettings { it.copy(registration = it.registration.copy(cameraVFovDeg = v)) }
            }
            Choice(
                listOf(0 to "0°", 1 to "90°", 2 to "180°", 3 to "270°"),
                s.registration.rotateQuarterTurns,
            ) { r -> vm.updateSettings { it.copy(registration = it.registration.copy(rotateQuarterTurns = r)) } }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = s.registration.mirrorX,
                    onCheckedChange = { m -> vm.updateSettings { it.copy(registration = it.registration.copy(mirrorX = m)) } },
                )
                Text("ToF 좌우 반전")
            }
        }

        Section("기타") {
            Choice(
                listOf("qvga" to "QVGA", "vga" to "VGA", "svga" to "SVGA", "xga" to "XGA", "uxga" to "UXGA"),
                s.photoSize,
            ) { size -> vm.updateSettings { it.copy(photoSize = size) } }
            NumberField("K (g / %p·L)", s.saltK, half, 1) { v ->
                if (v != null && v > 1.0) vm.updateSettings { it.copy(saltK = v) }
            }
        }
    }
}

@Composable
private fun <T> Choice(options: List<Pair<T, String>>, selected: T, onSelect: (T) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        options.forEach { (value, label) ->
            RadioButton(selected = value == selected, onClick = { onSelect(value) })
            Text(label, style = MaterialTheme.typography.bodySmall)
        }
    }
}
