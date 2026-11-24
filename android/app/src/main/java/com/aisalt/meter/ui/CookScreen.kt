package com.aisalt.meter.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aisalt.meter.analysis.AdditionKind
import com.aisalt.meter.analysis.GuideKind
import com.aisalt.meter.analysis.SolidsSource
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.data.Capture
import com.aisalt.meter.data.MeterUiState
import com.aisalt.meter.data.MeterViewModel

/** Cooking workflow: container (A), solids displacement (B), depth map (C), back-calculation (D). */
@Composable
fun CookScreen(st: MeterUiState, vm: MeterViewModel, modifier: Modifier) {
    val ready = st.link == LinkState.READY
    val busy = st.capture != Capture.NONE
    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        if (busy) Text("측정 대기 중: ${captureName(st.capture)}", color = MaterialTheme.colorScheme.primary)
        st.cook.message?.let { Text(it, style = MaterialTheme.typography.bodySmall) }

        FoodSection(st, vm)
        ContainerSection(st, vm, ready && !busy)
        SolidsSection(st, vm, ready && !busy)
        PlanSection(st, vm)
        AdjustSection(st, vm, ready && !busy)
    }
}

@Composable
private fun FoodSection(st: MeterUiState, vm: MeterViewModel) {
    Section("음식 / 조리 세션") {
        var food by remember { mutableStateOf(st.cook.foodName) }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(food, { food = it }, label = { Text("음식 이름 (학습 단위)") }, singleLine = true,
                modifier = Modifier.weight(1f))
            OutlinedButton(onClick = { vm.setFoodName(food) }) { Text("적용") }
        }
        val c = st.cook.correction
        KeyValue(
            "학습된 보정 (D)",
            if (c == null || c.count == 0) "없음" else "×${fmt(c.factor, 2)} (${c.count}회, 편차 ±${fmt(c.relSpread * 100, 0)}%)",
        )
        OutlinedButton(onClick = vm::newCookSession, modifier = Modifier.fillMaxWidth()) { Text("새 조리 시작 (기록 초기화)") }
    }
}

@Composable
private fun ContainerSection(st: MeterUiState, vm: MeterViewModel, enabled: Boolean) {
    Section("A. 용기 학습 (ToF로 A(h) 측정)") {
        Row(verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = st.activeProfile == null, onClick = { vm.setActiveProfile(null) })
            Text("설정 탭의 치수 사용")
        }
        st.profiles.forEach { p ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = st.activeProfile == p.name, onClick = { vm.setActiveProfile(p.name) })
                Text("${p.name}  (${p.points.size}점, 최대 ${fmt(p.points.maxOfOrNull { it.volumeMl }, 0)} mL)",
                    Modifier.weight(1f))
                TextButton(onClick = { vm.deleteProfile(p.name) }) { Text("삭제") }
            }
        }
        val l = st.learning
        if (l == null) {
            Text("빈 용기를 센서 아래 두고 시작합니다. 깊이는 설정 탭의 '안쪽 깊이'를 씁니다.",
                style = MaterialTheme.typography.bodySmall)
            Button(onClick = vm::startContainerLearning, enabled = enabled) { Text("용기 학습 시작 (빈 용기 측정)") }
        } else {
            KeyValue("바닥 거리 Dfloor", fmt(l.floorMm, 1, " mm"))
            l.points.forEachIndexed { i, p ->
                KeyValue("${i + 1}. 높이 ${fmt(p.heightMm, 1)} mm", "${fmt(p.volumeMl, 0)} mL")
            }
            l.equivalentDiameterMm?.let { KeyValue("마지막 구간 등가 지름", fmt(it, 0, " mm")) }
            l.message?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            var pour by remember { mutableStateOf<Double?>(100.0) }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NumberField("이번에 부은 물 mL", pour, Modifier.weight(1f), 0) { pour = it }
                Button(onClick = { pour?.let(vm::learnPour) }, enabled = enabled && (pour ?: 0.0) > 0) { Text("물 부음 측정") }
            }
            var name by remember { mutableStateOf("") }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(name, { name = it }, label = { Text("용기 이름") }, singleLine = true,
                    modifier = Modifier.weight(1f))
                Button(onClick = { vm.saveLearnedContainer(name) }, enabled = l.points.isNotEmpty()) { Text("저장") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = vm::learnUndo, enabled = l.points.isNotEmpty()) { Text("마지막 점 취소") }
                OutlinedButton(onClick = vm::cancelLearning) { Text("학습 취소") }
            }
        }
    }
}

@Composable
private fun SolidsSection(st: MeterUiState, vm: MeterViewModel, enabled: Boolean) {
    Section("B. 건더기 투입 변위 (넣기 전·후 ToF)") {
        KeyValue("조리 전 물(국물) 양", fmt(st.cook.initialLiquidMl, 0, " mL"))
        st.cook.solids.forEach { s ->
            KeyValue(
                "${s.label}: ${fmt(s.heightBeforeMm, 1)}→${fmt(s.heightAfterMm, 1)} mm",
                "${fmt(s.displacedMl, 0)} mL" + (s.alphaAfter?.let { "  α ${fmt(it, 2)}" } ?: ""),
            )
        }
        if (st.cook.solids.isNotEmpty()) KeyValue("건더기 합계", fmt(st.cook.solids.sumOf { it.displacedMl }, 0, " mL"))
        var label by remember { mutableStateOf("") }
        if (!st.cook.waitingForAfter) {
            Button(onClick = vm::solidsBefore, enabled = enabled, modifier = Modifier.fillMaxWidth()) {
                Text("① 건더기 넣기 전 측정")
            }
        } else {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(label, { label = it }, label = { Text("넣은 것 (예: 면, 두부)") }, singleLine = true,
                    modifier = Modifier.weight(1f))
                Button(onClick = { vm.solidsAfter(label); label = "" }, enabled = enabled) { Text("② 넣은 후 측정") }
            }
        }
    }
}

@Composable
private fun PlanSection(st: MeterUiState, vm: MeterViewModel) {
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let(vm::importDepthModel)
    }
    Section("국물 부피 결정 (A–D 융합)") {
        val plan = st.analysis?.plan
        val e = st.analysis?.estimate
        KeyValue("용기 모델", if (st.activeProfile != null) "학습 용기 '${st.activeProfile}'" else "치수 입력")
        KeyValue("수면 높이 H", fmt(e?.fillMm, 1, " mm"))
        KeyValue("전체 부피 Vtotal", fmt(plan?.totalMl, 0, " mL"))
        KeyValue("건더기 (${solidsSourceName(plan?.solidsSource)})", fmt(plan?.solidsMl, 0, " mL"))
        KeyValue("카메라+ToF 국물", estimateText(plan?.cameraTof?.valueMl, plan?.cameraTof?.relSigma))
        KeyValue("염도 역산 국물 (D)", estimateText(plan?.backCalc?.valueMl, plan?.backCalc?.relSigma))
        Text("최종 국물량: " + estimateText(plan?.final?.valueMl, plan?.final?.relSigma),
            fontWeight = FontWeight.Bold)
        plan?.notes?.forEach { Text("· $it", style = MaterialTheme.typography.bodySmall) }

        Text("C. 깊이 지도: ${st.depthModel ?: "모델 없음"}", style = MaterialTheme.typography.bodyMedium)
        st.analysis?.depth?.let { d ->
            KeyValue("ToF 스케일 맞춤", "${d.fit.zonesUsed}존 사용, ${d.fit.zonesRejected}존 제외, 오차 ${fmt(d.fit.medianErrorMm, 1)} mm")
            KeyValue("깊이 지도 수면 / 돌출 부피", "${fmt(d.surfaceMm, 1)} mm / ${fmt(d.aboveSurfaceMl, 0)} mL")
        }
        st.analysis?.depthNote?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
        OutlinedButton(onClick = { picker.launch(arrayOf("*/*")) }) { Text("깊이 모델(.onnx) 가져오기") }
    }
}

@Composable
private fun AdjustSection(st: MeterUiState, vm: MeterViewModel, enabled: Boolean) {
    Section("간 맞추기 (나눠 넣기 + 염도 역산)") {
        KeyValue("현재 / 목표", "${fmt(st.salinity?.pct, 2)} % → ${fmt(st.settings.targetPct, 2)} %")
        val g = st.guide
        val unit = if (g.kind == GuideKind.ADD_WATER) "mL" else "g"
        val what = if (g.kind == GuideKind.ADD_WATER) "물" else "소금"
        when (g.kind) {
            GuideKind.ADD_SALT, GuideKind.ADD_WATER -> {
                KeyValue("목표까지 전체", "$what ${fmt(g.amount, if (unit == "g") 1 else 0)} $unit")
                Text("지금 넣을 양: $what ${fmt(st.stepAmount, if (unit == "g") 1 else 0)} $unit",
                    style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                val ratio = st.analysis?.plan?.firstStepRatio
                if (st.cook.backCalc == null && ratio != null && ratio < 1.0) {
                    Text("부피 추정 불확실성 때문에 1차는 ${fmt(ratio * 100, 0)}%만 넣고 재측정합니다.",
                        style = MaterialTheme.typography.bodySmall)
                }
            }
            GuideKind.ON_TARGET -> Text("목표 도달 (±0.05%p)", style = MaterialTheme.typography.titleLarge)
            GuideKind.NO_DATA -> Text("염도를 먼저 측정하세요 (측정 탭)")
        }
        if (st.session.adviseManual) Text("반복 3회 초과: 수동 조정 또는 센서 보정 권장", color = MaterialTheme.colorScheme.error)

        var kind by remember { mutableStateOf(AdditionKind.SALT) }
        var amount by remember { mutableStateOf<Double?>(null) }
        LaunchedEffect(st.stepAmount, g.kind) {
            kind = if (g.kind == GuideKind.ADD_WATER) AdditionKind.WATER else AdditionKind.SALT
            amount = st.stepAmount?.takeIf { it > 0 }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = kind == AdditionKind.SALT, onClick = { kind = AdditionKind.SALT })
            Text("소금 g")
            RadioButton(selected = kind == AdditionKind.WATER, onClick = { kind = AdditionKind.WATER })
            Text("물 mL")
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            NumberField("실제로 넣은 양", amount, Modifier.weight(1f), 1) { amount = it }
            Button(
                onClick = { amount?.let { vm.recordAddition(kind, it) } },
                enabled = enabled && (amount ?: 0.0) > 0 && st.salinity?.pct != null,
            ) { Text("넣고 저음 → 재측정") }
        }
        st.cook.lastBackCalc?.let { KeyValue("마지막 역산", estimateText(it.valueMl, it.relSigma)) }
        st.cook.additions.forEachIndexed { i, a ->
            Text(
                "${i + 1}. ${if (a.kind == "SALT") "소금" else "물"} ${fmt(a.amount, 1)} " +
                    "${if (a.kind == "SALT") "g" else "mL"}: ${fmt(a.beforePct, 2)} → ${fmt(a.afterPct, 2)} %",
                style = MaterialTheme.typography.bodySmall,
            )
        }
        OutlinedButton(onClick = vm::applyToDevice, enabled = st.link == LinkState.READY) { Text("기기 OLED에 반영") }
    }
}

private fun estimateText(v: Double?, rel: Double?) =
    if (v == null) "—" else "${fmt(v, 0)} mL" + (rel?.let { " (±${fmt(it * 100, 0)}%)" } ?: "")

private fun solidsSourceName(s: SolidsSource?) = when (s) {
    SolidsSource.DISPLACEMENT -> "B 투입 변위"
    SolidsSource.DEPTH_MAP -> "C 깊이 지도"
    SolidsSource.AREA -> "면적식"
    SolidsSource.TOF_PROTRUSION -> "ToF 8×8 돌출"
    SolidsSource.NONE, null -> "없음"
}

private fun captureName(c: Capture) = when (c) {
    Capture.LEARN_FLOOR -> "빈 용기 바닥"
    Capture.LEARN_STEP -> "물 부은 후 수면"
    Capture.SOLIDS_BEFORE -> "건더기 넣기 전"
    Capture.SOLIDS_AFTER -> "건더기 넣은 후 (ToF + 사진)"
    Capture.ADDITION -> "투입 후 재측정"
    Capture.NONE -> ""
}
