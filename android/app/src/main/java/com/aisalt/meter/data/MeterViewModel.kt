package com.aisalt.meter.data

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aisalt.meter.analysis.AdditionKind
import com.aisalt.meter.analysis.AdditionRecord
import com.aisalt.meter.analysis.AdjustSession
import com.aisalt.meter.analysis.BackCalc
import com.aisalt.meter.analysis.BrothEstimate
import com.aisalt.meter.analysis.BrothEstimator
import com.aisalt.meter.analysis.BrothInputs
import com.aisalt.meter.analysis.CalPoint
import com.aisalt.meter.analysis.ColorSolidsSegmenter
import com.aisalt.meter.analysis.Container
import com.aisalt.meter.analysis.ContainerLearning
import com.aisalt.meter.analysis.ContainerProfile
import com.aisalt.meter.analysis.DepthFusion
import com.aisalt.meter.analysis.DepthSolidsResult
import com.aisalt.meter.analysis.DisplacementLedger
import com.aisalt.meter.analysis.Estimate
import com.aisalt.meter.analysis.FoodCorrection
import com.aisalt.meter.analysis.Fusion
import com.aisalt.meter.analysis.Guide
import com.aisalt.meter.analysis.GuideKind
import com.aisalt.meter.analysis.RelativeDepth
import com.aisalt.meter.analysis.RgbImage
import com.aisalt.meter.analysis.SaltGuide
import com.aisalt.meter.analysis.Segmentation
import com.aisalt.meter.analysis.SolidsAddition
import com.aisalt.meter.analysis.VolumePlan
import com.aisalt.meter.analysis.VolumePlanner
import com.aisalt.meter.ble.FoundDevice
import com.aisalt.meter.ble.LinkState
import com.aisalt.meter.ble.MeterBleManager
import com.aisalt.meter.ble.MeterScanner
import com.aisalt.meter.protocol.Commands
import com.aisalt.meter.protocol.DeviceEvent
import com.aisalt.meter.protocol.ImageAssembler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.abs

data class ImageInfo(
    val bitmap: Bitmap,
    val id: Int,
    val bytes: Int,
    val width: Int?,
    val height: Int?,
    val crcOk: Boolean,
    val transferMs: Long,
)

data class AnalysisResult(
    val segmentation: Segmentation?,
    /** Overlay for the downscaled analysis image (red = solid, blue = glare). */
    val overlay: Bitmap?,
    val estimate: BrothEstimate?,
    val depth: DepthSolidsResult?,
    val depthNote: String?,
    val plan: VolumePlan?,
)

data class SessionInfo(val rounds: Int = 0, val reached: Boolean = false, val adviseManual: Boolean = false)

/** Method A in progress. */
data class LearningUi(
    val floorMm: Double,
    val depthMm: Double,
    val points: List<CalPoint>,
    val message: String?,
    val equivalentDiameterMm: Double?,
)

/** Cooking session: methods B and D. */
data class CookUi(
    val foodName: String = "기본",
    val initialLiquidMl: Double? = null,
    val solids: List<SolidsAddition> = emptyList(),
    val waitingForAfter: Boolean = false,
    val additions: List<AdditionRecord> = emptyList(),
    val lastBackCalc: Estimate? = null,
    val backCalc: Estimate? = null,
    val correction: FoodCorrection? = null,
    val message: String? = null,
)

enum class Capture { NONE, LEARN_FLOOR, LEARN_STEP, SOLIDS_BEFORE, SOLIDS_AFTER, ADDITION }

data class MeterUiState(
    val link: LinkState = LinkState.DISCONNECTED,
    val linkNote: String? = null,
    val deviceName: String? = null,
    val scanning: Boolean = false,
    val found: List<FoundDevice> = emptyList(),
    val hello: DeviceEvent.Hello? = null,
    val salinity: DeviceEvent.Salinity? = null,
    val tof: DeviceEvent.Tof? = null,
    val deviceGuide: DeviceEvent.DeviceGuide? = null,
    val deviceSettings: DeviceEvent.Settings? = null,
    val image: ImageInfo? = null,
    val imageProgress: ImageAssembler.Progress? = null,
    val analysis: AnalysisResult? = null,
    val analyzing: Boolean = false,
    /** Guide for the full remaining amount, using the planned broth volume. */
    val guide: Guide = SaltGuide.compute(null, 0.8, null),
    /** Amount to add now (split addition until a back-calculation exists). */
    val stepAmount: Double? = null,
    val session: SessionInfo = SessionInfo(),
    val settings: AppSettings = AppSettings(),
    val profiles: List<ContainerProfile> = emptyList(),
    val activeProfile: String? = null,
    val learning: LearningUi? = null,
    val cook: CookUi = CookUi(),
    val capture: Capture = Capture.NONE,
    val depthModel: String? = null,
    val lastError: String? = null,
    val log: List<String> = emptyList(),
)

class MeterViewModel(app: Application) : AndroidViewModel(app) {
    private val store = SettingsStore(app)
    private val cookStore = CookStore(app)
    private val _state = MutableStateFlow(
        MeterUiState(
            settings = store.load(),
            profiles = cookStore.profiles(),
            activeProfile = cookStore.activeProfile(),
            cook = CookUi(foodName = cookStore.foodName()),
        ),
    )
    val state: StateFlow<MeterUiState> = _state.asStateFlow()

    private val assembler = ImageAssembler()
    private var imageStartedAt = 0L
    private var resendAttempts = 0
    private var finishedImageId = -1
    private var pendingRecheck = false
    private val session = AdjustSession(maxRounds = 3)
    private var analysisJob: Job? = null
    private var segmentation: Segmentation? = null
    private var overlay: Bitmap? = null
    private var analysisSource: Bitmap? = null
    private var relativeDepth: RelativeDepth? = null
    private var depthSource: Bitmap? = null
    private var depthEstimator: DepthEstimator? = null

    // Pending capture routing.
    private var learning: ContainerLearning? = null
    private var learnPourMl = 0.0
    private val ledger = DisplacementLedger()
    private var afterLabel = ""
    private var afterNeedsImageNewerThan = -1
    private var afterTofSeen = false
    private var pendingAddition: Pair<AdditionKind, Double>? = null
    private var additionBeforePct = 0.0
    private var lastSentBroth: Pair<Double, Double>? = null
    /** Set by a salinity event; consumed by the analysis run that completes after it. */
    private var salinityJudgementPending = false

    private val manager = MeterBleManager(
        app,
        onLine = ::onLine,
        onImagePacket = ::onImagePacket,
        onState = { s, note ->
            _state.update { it.copy(link = s, linkNote = note) }
            if (s == LinkState.DISCONNECTED || s == LinkState.FAILED) {
                pendingRecheck = false
                setCapture(Capture.NONE)
            }
        },
    )

    private val scanner = MeterScanner(app) { found ->
        _state.update { st ->
            val others = st.found.filterNot { it.device.address == found.device.address }
            st.copy(found = (others + found).sortedByDescending { it.rssi })
        }
    }

    init {
        loadDepthModel()
        _state.update { it.copy(cook = it.cook.copy(correction = correctionFor(it.cook.foodName))) }
    }

    // ------------------------------------------------------------ connection

    fun startScan() {
        _state.update { it.copy(found = emptyList()) }
        val ok = scanner.start()
        _state.update { it.copy(scanning = ok, lastError = if (ok) null else "Bluetooth off or unavailable") }
    }

    fun stopScan() {
        scanner.stop()
        _state.update { it.copy(scanning = false) }
    }

    fun connect(device: FoundDevice) {
        stopScan()
        _state.update { it.copy(deviceName = device.name, link = LinkState.CONNECTING) }
        viewModelScope.launch {
            runCatching { manager.connectTo(device.device) }
                .onFailure { e -> _state.update { it.copy(link = LinkState.FAILED, lastError = "connect: ${e.message}") } }
        }
    }

    fun disconnect() {
        viewModelScope.launch { runCatching { manager.disconnectNow() } }
    }

    // ------------------------------------------------------------ commands

    fun send(command: String) {
        if (command.isBlank()) return
        appendLog("> $command")
        viewModelScope.launch {
            runCatching { manager.send(command) }
                .onFailure { e -> _state.update { it.copy(lastError = "send '$command': ${e.message}") } }
        }
    }

    /** S100/S300: salinity only; starts a new adjustment round count. */
    fun measure() {
        pendingRecheck = false
        session.reset()
        send(Commands.MEASURE)
    }

    /** S200: ToF depth map + photo. */
    fun scan() = send(Commands.scan(_state.value.settings.photoSize))

    fun tofOnly() = send(Commands.TOF)

    /** S700 without recording an amount. Prefer [recordAddition]. */
    fun recheck() {
        pendingRecheck = true
        send(Commands.TOF)
        send(Commands.RECHECK)
    }

    /** Empty container in place: device stores Dfloor from its ToF. */
    fun captureFloorOnDevice() = send(Commands.FLOOR_FROM_TOF)

    /** Pushes target, container and the planned broth volume so the OLED guide matches the app. */
    fun applyToDevice() {
        val st = _state.value
        val s = st.settings
        send(Commands.target(s.targetPct))
        if (st.activeProfile == null) {
            Commands.bowl(s.container)?.let(::send)
            s.floorMm?.let { send(Commands.floor(it)) }
        }
        lastSentBroth = null
        syncBrothToDevice(force = true)
    }

    fun updateSettings(transform: (AppSettings) -> AppSettings) {
        val next = transform(_state.value.settings)
        store.save(next)
        _state.update { it.copy(settings = next) }
        reanalyze(resegment = true)
    }

    fun clearError() = _state.update { it.copy(lastError = null) }

    // ------------------------------------------------------------ A: container learning

    fun startContainerLearning() {
        learning = null
        _state.update { it.copy(learning = null) }
        setCapture(Capture.LEARN_FLOOR)
        send(Commands.TOF)
    }

    fun learnPour(ml: Double) {
        if (learning == null || ml <= 0) return
        learnPourMl = ml
        setCapture(Capture.LEARN_STEP)
        send(Commands.TOF)
    }

    fun learnUndo() {
        learning?.undo()
        publishLearning(null)
    }

    fun saveLearnedContainer(name: String) {
        val profile = learning?.profile(name.trim().ifEmpty { "용기" }) ?: return
        cookStore.saveProfile(profile)
        cookStore.setActiveProfile(profile.name)
        learning = null
        _state.update {
            it.copy(learning = null, profiles = cookStore.profiles(), activeProfile = profile.name)
        }
        reanalyze(resegment = false)
    }

    fun cancelLearning() {
        learning = null
        setCapture(Capture.NONE)
        _state.update { it.copy(learning = null) }
    }

    fun setActiveProfile(name: String?) {
        cookStore.setActiveProfile(name)
        _state.update { it.copy(activeProfile = name) }
        reanalyze(resegment = false)
    }

    fun deleteProfile(name: String) {
        cookStore.deleteProfile(name)
        _state.update { it.copy(profiles = cookStore.profiles(), activeProfile = cookStore.activeProfile()) }
        reanalyze(resegment = false)
    }

    private fun publishLearning(message: String?) {
        val l = learning
        _state.update {
            it.copy(
                learning = l?.let { x ->
                    LearningUi(x.floorMm, x.depthMm, x.points.toList(), message, x.lastEquivalentDiameterMm())
                },
            )
        }
    }

    // ------------------------------------------------------------ B + D: cooking session

    fun newCookSession() {
        ledger.clear()
        session.reset()
        pendingAddition = null
        pendingRecheck = false
        lastSentBroth = null
        setCapture(Capture.NONE)
        _state.update { it.copy(cook = CookUi(foodName = it.cook.foodName, correction = it.cook.correction)) }
        send(Commands.BROTH_CLEAR)
        reanalyze(resegment = false)
    }

    fun setFoodName(name: String) {
        val food = name.trim().ifEmpty { "기본" }
        cookStore.setFoodName(food)
        _state.update { it.copy(cook = it.cook.copy(foodName = food, correction = correctionFor(food))) }
        reanalyze(resegment = false)
    }

    /** B: surface before adding solids (also records the pre-cooking liquid the first time). */
    fun solidsBefore() {
        setCapture(Capture.SOLIDS_BEFORE)
        send(Commands.TOF)
    }

    /** B: surface (and photo) right after adding solids. */
    fun solidsAfter(label: String) {
        if (!ledger.waitingForAfter) return
        afterLabel = label.trim().ifEmpty { "건더기" }
        afterTofSeen = false
        afterNeedsImageNewerThan = if (_state.value.hello?.camera == true) (_state.value.image?.id ?: -1) else Int.MAX_VALUE
        setCapture(Capture.SOLIDS_AFTER)
        if (afterNeedsImageNewerThan == Int.MAX_VALUE) send(Commands.TOF)
        else send(Commands.scan(_state.value.settings.photoSize))
    }

    /** D: the user added [amount] (g salt / mL water) and mixed; re-measure and back-calculate. */
    fun recordAddition(kind: AdditionKind, amount: Double) {
        val before = _state.value.salinity?.pct
        if (before == null || amount <= 0) {
            _state.update { it.copy(lastError = "염도를 먼저 측정하고 투입량을 입력하세요") }
            return
        }
        pendingAddition = kind to amount
        additionBeforePct = before
        pendingRecheck = true
        setCapture(Capture.ADDITION)
        send(Commands.TOF)
        send(Commands.RECHECK)
    }

    // ------------------------------------------------------------ C: depth model

    fun importDepthModel(uri: Uri) {
        viewModelScope.launch {
            val ok = withContext(Dispatchers.IO) {
                runCatching {
                    val target = DepthEstimator.modelFile(getApplication<Application>().filesDir)
                    target.parentFile?.mkdirs()
                    getApplication<Application>().contentResolver.openInputStream(uri)!!.use { input ->
                        target.outputStream().use { input.copyTo(it) }
                    }
                }.isSuccess
            }
            if (!ok) _state.update { it.copy(lastError = "모델 파일을 복사하지 못했습니다") }
            loadDepthModel()
            relativeDepth = null
            reanalyze(resegment = true)
        }
    }

    private fun loadDepthModel() {
        depthEstimator?.close()
        depthEstimator = null
        val file = DepthEstimator.modelFile(getApplication<Application>().filesDir)
        if (file.exists()) {
            depthEstimator = runCatching { DepthEstimator(file) }
                .onFailure { e -> _state.update { it.copy(lastError = "깊이 모델 로드 실패: ${e.message}") } }
                .getOrNull()
        }
        _state.update { it.copy(depthModel = depthEstimator?.description) }
    }

    // ------------------------------------------------------------ device events

    private fun onLine(line: String) {
        appendLog(line)
        when (val e = DeviceEvent.parse(line)) {
            is DeviceEvent.Hello -> {
                _state.update { it.copy(hello = e) }
                if (!e.timeSet) send(Commands.time(System.currentTimeMillis() / 1000))
            }
            is DeviceEvent.Salinity -> onSalinity(e)
            is DeviceEvent.Tof -> {
                _state.update { it.copy(tof = e) }
                onTofCapture(e)
                reanalyze(resegment = false)
            }
            is DeviceEvent.DeviceGuide -> _state.update { it.copy(deviceGuide = e) }
            is DeviceEvent.Settings -> {
                _state.update { it.copy(deviceSettings = e) }
                val deviceFloor = e.double("floorMm")
                if (deviceFloor != null && _state.value.settings.floorMm != deviceFloor) {
                    updateSettings { it.copy(floorMm = deviceFloor) }
                }
            }
            is DeviceEvent.ImageBegin -> {
                assembler.begin(e)
                imageStartedAt = System.currentTimeMillis()
                resendAttempts = 0
                _state.update { it.copy(imageProgress = assembler.progress()) }
                tryFinishImage()
            }
            is DeviceEvent.ImageEnd -> {
                if (!tryFinishImage()) requestMissingChunks()
            }
            is DeviceEvent.Error -> {
                _state.update { it.copy(lastError = "${e.op}: ${e.code} ${e.msg ?: ""}") }
                // A failed photo must not leave the "after" capture waiting forever.
                if (_state.value.capture == Capture.SOLIDS_AFTER && e.op == "photo") afterNeedsImageNewerThan = Int.MAX_VALUE
            }
            else -> Unit
        }
    }

    private fun onSalinity(e: DeviceEvent.Salinity) {
        _state.update { it.copy(salinity = e) }
        val addition = pendingAddition
        if (addition != null && e.pct != null) {
            pendingAddition = null
            applyBackCalculation(AdditionRecord(addition.first.name, addition.second, additionBeforePct, e.pct, System.currentTimeMillis()))
        }
        if (_state.value.capture == Capture.ADDITION) setCapture(Capture.NONE)
        salinityJudgementPending = true
        reanalyze(resegment = false)
    }

    /** D: back-calculate, carry the previous estimate forward, fuse, and learn. */
    private fun applyBackCalculation(record: AdditionRecord) {
        val cook = _state.value.cook
        val st = _state.value
        val estimate = BackCalc.brothAfter(record, st.settings.saltK)
        val carried = cook.backCalc?.let { prev ->
            if (record.additionKind == AdditionKind.WATER) {
                val v = prev.valueMl + record.amount
                Estimate(v, prev.sigmaMl / v, prev.source)
            } else prev
        }
        var correction = cook.correction
        val message: String
        val fused: Estimate?
        if (estimate != null) {
            fused = Fusion.combine(listOfNotNull(carried, estimate))
            val raw = st.analysis?.plan?.cameraTofRaw
            if (raw != null) {
                correction = (correction ?: FoodCorrection(cook.foodName)).observe(estimate, raw)
                cookStore.saveCorrection(correction)
            }
            message = "역산 국물량 %.0f mL (±%.0f%%)".format(estimate.valueMl, estimate.relSigma * 100)
        } else {
            fused = carried
            message = "염도 변화가 작아 역산하지 않았습니다 (투입량을 늘리면 정확해집니다)"
        }
        _state.update {
            it.copy(
                cook = it.cook.copy(
                    additions = it.cook.additions + record,
                    lastBackCalc = estimate ?: it.cook.lastBackCalc,
                    backCalc = fused,
                    correction = correction,
                    message = message,
                ),
            )
        }
    }

    /** Routes a ToF frame to the capture the user started. */
    private fun onTofCapture(e: DeviceEvent.Tof) {
        val grid = e.grid
        if (grid.size != 64) return
        val center = BrothEstimator.estimate(
            BrothInputs(grid, null, Container.Rect(1.0, 1.0, 1.0), null),
        ).surfaceMm
        when (_state.value.capture) {
            Capture.LEARN_FLOOR -> {
                setCapture(Capture.NONE)
                if (center == null) return publishLearning("ToF 유효 영역이 부족합니다")
                learning = ContainerLearning(center, _state.value.settings.depthMm)
                publishLearning("바닥 거리 %.1f mm 저장. 계량한 물을 붓고 '물 부음'을 누르세요".format(center))
            }
            Capture.LEARN_STEP -> {
                setCapture(Capture.NONE)
                val l = learning ?: return
                if (center == null) return publishLearning("ToF 유효 영역이 부족합니다")
                when (val r = l.addStep(learnPourMl, center)) {
                    is ContainerLearning.StepResult.Added ->
                        publishLearning("높이 %.1f mm, 누적 %.0f mL".format(r.point.heightMm, r.point.volumeMl))
                    is ContainerLearning.StepResult.Rejected -> publishLearning("거부: ${r.reason}")
                }
            }
            Capture.SOLIDS_BEFORE -> {
                setCapture(Capture.NONE)
                val (container, floor) = activeContainer()
                if (center == null || floor == null) {
                    cookMessage("바닥 기준거리 또는 ToF 값이 없습니다")
                    return
                }
                ledger.markBefore(container, floor - center)
                publishLedger("넣기 전 수면 높이 %.1f mm. 건더기를 넣고 '넣은 후 측정'을 누르세요".format(floor - center))
            }
            Capture.SOLIDS_AFTER -> afterTofSeen = true
            else -> Unit
        }
    }

    /** Finishes B once both the ToF and (if a camera exists) the new photo are analysed. */
    private fun maybeFinishSolidsAfter(estimate: BrothEstimate?, seg: Segmentation?) {
        if (_state.value.capture != Capture.SOLIDS_AFTER || !afterTofSeen) return
        val imageReady = afterNeedsImageNewerThan == Int.MAX_VALUE ||
            (_state.value.image?.id ?: -1) > afterNeedsImageNewerThan
        if (!imageReady || estimate?.fillMm == null) return
        setCapture(Capture.NONE)
        val (container, _) = activeContainer()
        val entry = ledger.markAfter(container, estimate.fillMm, afterLabel, seg?.alpha, System.currentTimeMillis())
        publishLedger(entry?.let { "'${it.label}' 변위 %.0f mL".format(it.displacedMl) } ?: "넣기 전 측정이 없습니다")
        reanalyze(resegment = false)
    }

    private fun publishLedger(message: String) {
        _state.update {
            it.copy(
                cook = it.cook.copy(
                    initialLiquidMl = ledger.initialLiquidMl,
                    solids = ledger.additions.toList(),
                    waitingForAfter = ledger.waitingForAfter,
                    message = message,
                ),
            )
        }
    }

    private fun cookMessage(message: String) = _state.update { it.copy(cook = it.cook.copy(message = message)) }

    private fun setCapture(c: Capture) = _state.update { it.copy(capture = c) }

    private fun correctionFor(food: String) = cookStore.corrections().firstOrNull { it.food == food }

    private fun activeContainer(): Pair<Container, Double?> {
        val st = _state.value
        val profile = st.profiles.firstOrNull { it.name == st.activeProfile }
        return if (profile != null) profile.container() to profile.floorMm
        else st.settings.container to (st.settings.floorMm ?: st.tof?.floorMm)
    }

    // ------------------------------------------------------------ image transfer

    private fun onImagePacket(packet: ByteArray) {
        if (!assembler.accept(packet)) return
        val p = assembler.progress() ?: return
        val step = maxOf(1, p.total / 20)
        if (p.received % step == 0 || p.received == p.total) _state.update { it.copy(imageProgress = p) }
        tryFinishImage()
    }

    private fun requestMissingChunks() {
        val meta = assembler.current ?: return
        val missing = assembler.missing()
        if (missing.isEmpty()) return
        if (resendAttempts >= 3 || missing.size > 200) {
            _state.update { it.copy(lastError = "image ${meta.id}: ${missing.size} chunks missing") }
            return
        }
        resendAttempts++
        Commands.resendChunks(meta.id, missing).forEach(::send)
    }

    private fun tryFinishImage(): Boolean {
        val meta = assembler.current ?: return false
        if (!assembler.isComplete) return false
        if (finishedImageId == meta.id) return true
        finishedImageId = meta.id
        val crcOk = assembler.crcMatches() == true
        val bytes = assembler.result()
        val elapsed = System.currentTimeMillis() - imageStartedAt
        if (bytes == null) {
            _state.update { it.copy(lastError = "image ${meta.id}: CRC mismatch") }
            return true
        }
        viewModelScope.launch {
            val bitmap = withContext(Dispatchers.Default) { BitmapFactory.decodeByteArray(bytes, 0, bytes.size) }
            if (bitmap == null) {
                _state.update { it.copy(lastError = "image ${meta.id}: JPEG decode failed") }
                return@launch
            }
            _state.update {
                it.copy(image = ImageInfo(bitmap, meta.id, bytes.size, meta.width, meta.height, crcOk, elapsed))
            }
            reanalyze(resegment = true)
        }
        return true
    }

    // ------------------------------------------------------------ analysis (S400 - S600, A-D)

    private fun reanalyze(resegment: Boolean) {
        analysisJob?.cancel()
        analysisJob = viewModelScope.launch {
            val st = _state.value
            val s = st.settings
            _state.update { it.copy(analyzing = true) }
            val bitmap = st.image?.bitmap
            withContext(Dispatchers.Default) {
                if (bitmap != null && (resegment || segmentation == null || analysisSource !== bitmap)) {
                    val small = scaleForAnalysis(bitmap)
                    val pixels = IntArray(small.width * small.height)
                    small.getPixels(pixels, 0, small.width, 0, 0, small.width, small.height)
                    val seg = ColorSolidsSegmenter(deltaEThreshold = s.deltaEThreshold)
                        .segment(RgbImage(small.width, small.height, pixels), s.bowl)
                    segmentation = seg
                    overlay = overlayBitmap(seg)
                    analysisSource = bitmap
                }
                // C: relative depth once per photo.
                val estimator = depthEstimator
                if (bitmap != null && estimator != null && depthSource !== bitmap) {
                    relativeDepth = runCatching { estimator.estimate(bitmap) }.getOrNull()
                    depthSource = bitmap
                }
            }
            val (container, floor) = activeContainer()
            val grid = st.tof?.grid
            var depthResult: DepthSolidsResult? = null
            var depthNote: String? = null
            val estimate = if (grid != null && grid.size == 64) {
                withContext(Dispatchers.Default) {
                    val seg = segmentation
                    val rel = relativeDepth
                    if (rel != null && seg != null) {
                        val fit = DepthFusion.fit(rel, grid, s.registration)
                        if (fit == null) depthNote = "깊이 지도 스케일 맞춤 실패 (유효 ToF 존 부족 또는 깊이 변화 없음)"
                        else depthResult = DepthFusion.solidsAboveSurface(rel, fit, seg, s.registration)
                    } else if (depthEstimator == null) {
                        depthNote = "깊이 모델 없음: 8×8 ToF 돌출식 사용"
                    }
                    BrothEstimator.estimate(
                        BrothInputs(
                            tofGrid = grid,
                            floorMm = floor,
                            container = container,
                            segmentation = seg,
                            registration = s.registration,
                            solids = s.solids,
                        ),
                    )
                }
            } else null

            val cook = _state.value.cook
            val plan = VolumePlanner.plan(
                total = estimate?.totalMl,
                calibratedContainer = container is Container.Calibrated,
                displacementMl = if (ledger.additions.isNotEmpty()) ledger.totalSolidsMl else null,
                depthSolidsMl = depthResult?.let { it.aboveSurfaceMl * s.solids.gammaProtrusion },
                areaSolidsMl = estimate?.solidsAreaMl,
                tofSolidsMl = estimate?.solidsProtrusionMl,
                correction = cook.correction?.takeIf { it.count > 0 },
                backCalc = cook.backCalc,
            )
            val broth = plan.final?.valueMl ?: estimate?.brothMl
            val pct = _state.value.salinity?.pct
            val guide = SaltGuide.compute(pct, s.targetPct, broth, s.saltK)
            val step = when {
                guide.amount == null || guide.kind == GuideKind.ON_TARGET -> guide.amount
                cook.backCalc == null -> guide.amount * plan.firstStepRatio
                else -> guide.amount
            }
            val judged = salinityJudgementPending && pct != null
            if (judged) {
                salinityJudgementPending = false
                if (pendingRecheck) {
                    session.onRemeasured(guide)
                    pendingRecheck = false
                } else if (session.rounds == 0) {
                    session.onFirstMeasurement(guide)
                }
            }
            _state.update {
                it.copy(
                    analysis = AnalysisResult(segmentation, overlay, estimate, depthResult, depthNote, plan),
                    guide = guide,
                    stepAmount = step,
                    session = SessionInfo(session.rounds, session.reached, session.adviseManual),
                    analyzing = false,
                )
            }
            maybeFinishSolidsAfter(estimate, segmentation)
            if (judged) syncBrothToDevice(force = false)
        }
    }

    /** Keeps the device OLED guide on the app's broth volume and split ratio. */
    private fun syncBrothToDevice(force: Boolean) {
        if (_state.value.link != LinkState.READY) return
        val plan = _state.value.analysis?.plan ?: return
        val broth = plan.final?.valueMl ?: return
        val ratio = if (_state.value.cook.backCalc == null) plan.firstStepRatio else 1.0
        val last = lastSentBroth
        if (!force && last != null && abs(last.first - broth) < broth * 0.01 && abs(last.second - ratio) < 0.01) return
        lastSentBroth = broth to ratio
        send(Commands.broth(broth, ratio))
    }

    private fun scaleForAnalysis(src: Bitmap): Bitmap {
        val maxSide = 240
        val scale = maxSide.toDouble() / maxOf(src.width, src.height)
        if (scale >= 1.0) return src
        return Bitmap.createScaledBitmap(src, (src.width * scale).toInt(), (src.height * scale).toInt(), true)
    }

    private fun overlayBitmap(seg: Segmentation): Bitmap {
        val colors = IntArray(seg.width * seg.height) { i ->
            when (seg.labels[i]) {
                Segmentation.SOLID -> Color.argb(150, 255, 40, 40)
                Segmentation.GLARE -> Color.argb(150, 40, 120, 255)
                Segmentation.OUTSIDE -> Color.argb(110, 0, 0, 0)
                else -> Color.TRANSPARENT
            }
        }
        return Bitmap.createBitmap(colors, seg.width, seg.height, Bitmap.Config.ARGB_8888)
    }

    // ------------------------------------------------------------ log

    private val clock = SimpleDateFormat("HH:mm:ss", Locale.US)

    private fun appendLog(line: String) {
        val stamped = "${clock.format(Date())} $line"
        _state.update { it.copy(log = (it.log + stamped).takeLast(300)) }
    }

    override fun onCleared() {
        scanner.stop()
        manager.close()
        depthEstimator?.close()
        super.onCleared()
    }
}
