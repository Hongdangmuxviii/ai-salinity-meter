package com.aisalt.meter.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aisalt.meter.analysis.GuideKind
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.data.MeterUiState
import com.aisalt.meter.data.MeterViewModel

@Composable
fun MeasureScreen(st: MeterUiState, vm: MeterViewModel, modifier: Modifier) {
    val ready = st.link == LinkState.READY
    var showOverlay by remember { mutableStateOf(true) }

    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        // S100-S200 / S700 actions
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = vm::measure, enabled = ready, modifier = Modifier.weight(1f)) { Text("염도 측정") }
            Button(onClick = vm::scan, enabled = ready, modifier = Modifier.weight(1f)) { Text("스캔(ToF+사진)") }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = vm::tofOnly, enabled = ready, modifier = Modifier.weight(1f)) { Text("ToF만") }
            OutlinedButton(onClick = vm::recheck, enabled = ready, modifier = Modifier.weight(1f)) { Text("투입 완료→재측정") }
        }

        // S300 current salinity
        Section("현재 염도 (S300)") {
            val s = st.salinity
            Text(
                if (s?.pct != null) fmt(s.pct, 2, " %") else if (s != null) "모델 범위 밖" else "측정 전",
                style = MaterialTheme.typography.headlineMedium,
            )
            if (s != null) {
                KeyValue("온도", fmt(s.tempC, 2, " ℃"))
                KeyValue("보정 범위", s.span ?: "—")
                KeyValue("응답 인덱스", fmt(s.index, 3))
                if (s.unstable) Text("3회 측정 편차가 큼: 재측정 권장", color = MaterialTheme.colorScheme.error)
                if (!s.temperatureCompensated) Text("온도보정 미적용 (기기 tcomp 꺼짐)", style = MaterialTheme.typography.bodySmall)
            }
        }

        // S600 guide
        Section("투입 가이드 (S500–S700)") {
            val g = st.guide
            val text = when (g.kind) {
                GuideKind.ADD_SALT -> "소금 ${fmt(g.amount, 1)} g 추가" + if (g.perLiter) " (국물 1 L당)" else ""
                GuideKind.ADD_WATER -> "물 ${fmt(g.amount, 0)} mL 추가" + if (g.perLiter) " (국물 1 L당)" else ""
                GuideKind.ON_TARGET -> "목표 도달 (±0.05%p)"
                GuideKind.NO_DATA -> "염도를 먼저 측정하세요"
            }
            Text(text, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            if (g.kind == GuideKind.ADD_SALT || g.kind == GuideKind.ADD_WATER) {
                Text(
                    "지금 넣을 양: ${fmt(st.stepAmount, if (g.kind == GuideKind.ADD_SALT) 1 else 0)} ${g.unit} (조리 탭에서 투입 기록)",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NumberField("목표 염도 %", st.settings.targetPct, Modifier.weight(1f)) { v ->
                    if (v != null && v in 0.3..3.0) vm.updateSettings { it.copy(targetPct = v) }
                }
                OutlinedButton(onClick = vm::applyToDevice, enabled = ready) { Text("기기에 적용") }
            }
            KeyValue("기준 국물량", fmt(st.analysis?.plan?.final?.valueMl ?: st.analysis?.estimate?.brothMl, 0, " mL"))
            KeyValue("재측정 회차", "${st.session.rounds}")
            if (st.session.adviseManual) {
                Text("반복 3회 초과: 수동 조정 또는 센서 보정 권장", color = MaterialTheme.colorScheme.error)
            }
            st.deviceGuide?.let { d ->
                Text(
                    "기기 계산: ${d.kind ?: "—"} ${fmt(d.amount, 1)} ${d.unit ?: ""}" +
                        " (국물 ${fmt(d.brothMl, 0)} mL)",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }

        // S400 volume
        Section("국물 부피 (S400)") {
            val e = st.analysis?.estimate
            if (e == null) {
                Text("ToF 데이터 없음 — 스캔하세요")
            } else {
                KeyValue("수면 거리 / 바닥 기준", "${fmt(e.surfaceMm, 1)} / ${fmt(st.settings.floorMm ?: st.tof?.floorMm, 1)} mm")
                KeyValue("수면 높이 H", fmt(e.fillMm, 1, " mm"))
                KeyValue("전체 부피 Vtotal", fmt(e.totalMl, 0, " mL"))
                KeyValue("건더기 면적비 α", fmt(e.alpha, 3))
                KeyValue("Vsolid (면적식 / 돌출식)", "${fmt(e.solidsAreaMl, 0)} / ${fmt(e.solidsProtrusionMl, 0)} mL")
                KeyValue("Vsolid 적용 (${st.settings.solids.method})", fmt(e.solidsMl, 0, " mL"))
                KeyValue("국물 부피 Vbroth", fmt(e.brothMl, 0, " mL"))
                KeyValue("국물 존 / 건더기 존", "${e.brothZones} / ${e.solidZones}")
                e.notes.forEach { Text("· $it", style = MaterialTheme.typography.bodySmall) }
            }
            if (st.analyzing) Text("분석 중…", style = MaterialTheme.typography.bodySmall)
        }

        // S200 image + solids mask
        Section("사진 / 건더기 영역") {
            st.imageProgress?.let { p ->
                if (st.image?.id != p.id) Text("사진 수신 중 ${p.received}/${p.total}")
            }
            val img = st.image
            if (img == null) {
                Text("사진 없음")
            } else {
                val kbps = if (img.transferMs > 0) img.bytes / 1.024 / img.transferMs else null
                Text(
                    "#${img.id}  ${img.width}×${img.height}  ${img.bytes / 1024} KB  " +
                        "${img.transferMs} ms (${fmt(kbps, 1)} KB/s)  CRC ${if (img.crcOk) "OK" else "불일치"}",
                    style = MaterialTheme.typography.bodySmall,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = showOverlay, onCheckedChange = { showOverlay = it })
                    Text("건더기(빨강)·반사(파랑) 표시")
                }
                val ratio = img.bitmap.width.toFloat() / img.bitmap.height
                Box(Modifier.fillMaxWidth().aspectRatio(ratio)) {
                    Image(img.bitmap.asImageBitmap(), null, Modifier.fillMaxWidth().aspectRatio(ratio), contentScale = ContentScale.FillBounds)
                    val overlay = st.analysis?.overlay
                    if (showOverlay && overlay != null) {
                        Image(overlay.asImageBitmap(), null, Modifier.fillMaxWidth().aspectRatio(ratio), contentScale = ContentScale.FillBounds)
                    }
                }
                st.analysis?.segmentation?.let { seg ->
                    Text(
                        "α = ${fmt(seg.alpha, 3)}  (방식 ${seg.method}, 국물 Lab ${fmt(seg.brothColor.l, 0)}/" +
                            "${fmt(seg.brothColor.a, 0)}/${fmt(seg.brothColor.b, 0)})",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
