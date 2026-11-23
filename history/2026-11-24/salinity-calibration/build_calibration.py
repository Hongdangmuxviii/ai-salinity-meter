import csv
import json
import re
from pathlib import Path
from statistics import median, stdev

ROOT=Path(__file__).resolve().parent
BASE=Path(r"C:\Users\Yeon\Documents\Codex\2026-11-23\sensor-recheck\diagnostic")
PATTERN=re.compile(r"CURRENT_RESULT temp_C=([\d.]+) index=([\d.]+)")

def reference(pattern, percent):
    for path in sorted(ROOT.glob(pattern),reverse=True):
        values=[tuple(map(float,m)) for m in PATTERN.findall(path.read_text(encoding="utf-8-sig"))]
        if len(values)==3 and "STOP:" not in path.read_text(encoding="utf-8-sig"):
            indices=[v[1] for v in values]
            return dict(reference_percent=percent, index=median(indices),
                        temperature_C=median(v[0] for v in values),
                        trial_indices=indices, trial_sample_stdev=stdev(indices), source=str(path))
    raise ValueError(f"Complete reference not yet available: {pattern}")

lo=reference("reference_0p6_ready_*_raw.txt",0.6)
hi=reference("reference_2p0_*_raw.txt",2.0)
if not (0<lo["index"]<hi["index"]<100):
    raise ValueError("Reference responses must be monotonic and below100 for this divider transform")
g0=lo["index"]/(100-lo["index"])
g1=hi["index"]/(100-hi["index"])
gain=(hi["reference_percent"]-lo["reference_percent"])/(g1-g0)
offset=lo["reference_percent"]-gain*g0
model=dict(id="REF_06_20_20261124_V1", response="C=200*(A1-A3)/(A2-A3)",
           transform="G=C/(100-C)", estimate="percent=gain*G+offset",
           gain=gain,offset=offset,low=lo,high=hi,aggregation="median of3 unchanged k acquisitions",
           source="user comparison salinity meter",temperature_compensated=False,
           accuracy_independently_validated=False,
           scope="Two-point comparative prototype calibration over0.6..2.0% at recorded conditions; not certified standards.")
ROOT.mkdir(exist_ok=True)
(ROOT/"calibration_model.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
with (ROOT/"calibration_references.csv").open("w",encoding="utf-8-sig",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=["reference_percent","trial","response_index","temperature_C","source"])
    writer.writeheader()
    for r in (lo,hi):
        for i,value in enumerate(r["trial_indices"],1):
            writer.writerow(dict(reference_percent=r["reference_percent"],trial=i,response_index=value,
                                 temperature_C=r["temperature_C"],source=r["source"]))

sketch=ROOT/"SalinityMeterCalibrated"
sketch.mkdir(exist_ok=True)
header=f'''#pragma once
// Comparative calibration, NOT an independently validated accuracy specification.
constexpr char calibrationId[] = "{model['id']}";
constexpr double calibrationGain = {gain:.15g};
constexpr double calibrationOffset = {offset:.15g};
constexpr double calibrationIndexLow = {lo['index']:.10f};
constexpr double calibrationIndexHigh = {hi['index']:.10f};
constexpr double calibrationPercentLow = 0.6;
constexpr double calibrationPercentHigh = 2.0;
constexpr double calibrationTempLowReference = {lo['temperature_C']:.5f};
constexpr double calibrationTempHighReference = {hi['temperature_C']:.5f};
'''
(sketch/"CalibrationTable.h").write_text(header,encoding="utf-8")
src=(BASE/"HeadDifferentialDiagnostic"/"HeadDifferentialDiagnostic.ino").read_text(encoding="utf-8-sig")
src=src.replace("#include <DallasTemperature.h>","#include <DallasTemperature.h>\n#include \"CalibrationTable.h\"")
start=src.index("void runCurrentMeasurement(float celsius) {")
end=src.index("\nvoid setup() {",start)
part=src[start:end]
part=part.replace("void runCurrentMeasurement(float celsius) {",
                  "float lastCurrentIndex = NAN;\n\nvoid runCurrentMeasurement(float celsius) {\n  lastCurrentIndex = NAN;")
part=part.replace('  Serial.printf("CURRENT_RESULT',
                  '  lastCurrentIndex = (forward + reverse) / 2.0f;\n  Serial.printf("CURRENT_RESULT')
src=src[:start]+part+src[end:]
helpers=r'''
void printCalibration() {
  Serial.printf("CAL_TABLE id=%s gain=%.12f offset=%.12f index_low=%.5f index_high=%.5f reference_low=%.1f reference_high=%.1f temp_low_reference_C=%.2f temp_high_reference_C=%.2f aggregation=median3 temperature_compensated=false\n",
    calibrationId, calibrationGain, calibrationOffset, calibrationIndexLow, calibrationIndexHigh,
    calibrationPercentLow, calibrationPercentHigh, calibrationTempLowReference, calibrationTempHighReference);
}

void runCalibratedMeasurement() {
  float indices[3], temperatures[3];
  for (uint8_t i=0; i<3; ++i) {
    if (!readTemperature(temperatures[i])) return;
    runCurrentMeasurement(temperatures[i]);
    if (!isfinite(lastCurrentIndex)) return;
    indices[i]=lastCurrentIndex;
    delay(200);
  }
  if (indices[0]>indices[1]) { float t=indices[0]; indices[0]=indices[1]; indices[1]=t; }
  if (indices[1]>indices[2]) { float t=indices[1]; indices[1]=indices[2]; indices[2]=t; }
  if (indices[0]>indices[1]) { float t=indices[0]; indices[0]=indices[1]; indices[1]=t; }
  const double index=indices[1];
  if (!(index>0.0 && index<100.0)) {
    Serial.printf("SALINITY_RESULT response_index=%.5f status=OUTSIDE_MODEL_DOMAIN drive=INPUT\n",index);
    return;
  }
  const double proxy=index/(100.0-index);
  const double estimatedPercent=calibrationGain*proxy+calibrationOffset;
  const char *status=index<calibrationIndexLow ? "BELOW_REFERENCE_SPAN" :
                     index>calibrationIndexHigh ? "ABOVE_REFERENCE_SPAN" : "IN_REFERENCE_SPAN";
  Serial.printf("SALINITY_RESULT estimate_percent=%.3f response_index=%.5f temp_C=%.2f status=%s calibration_id=%s median_of=3 temperature_compensated=false accuracy_independently_validated=false\n",
    estimatedPercent,index,temperatures[2],status,calibrationId);
}
'''
src=src.replace("\nvoid setup() {","\n"+helpers+"\nvoid setup() {")
old_ready='READY CURRENT_RATIO_V1: k=current-derived response, t=temp, m=legacy, d/e/f/g/s=prior diagnostics, c=electrical check. Drive idle.'
src=src.replace(old_ready,'READY SALINITY_CAL_2P_V1: m=calibrated estimate(median3), k=raw response, p=calibration table, t=temperature. Drive idle.')
loop=r'''
void loop() {
  if (!Serial.available()) { delay(1); return; }
  const char command=Serial.read();
  if (command=='p') { printCalibration(); return; }
  if (command!='m' && command!='k' && command!='t') return;
  if (command=='m') {
    if (ready) runCalibratedMeasurement();
    else Serial.println("STOP: ADS1115 missing.");
    return;
  }
  float celsius;
  if (!readTemperature(celsius)) return;
  if (command=='t') { Serial.printf("TEMP temp_C=%.2f\n",celsius); return; }
  if (!ready) { Serial.println("STOP: ADS1115 missing."); return; }
  runCurrentMeasurement(celsius);
}
'''
src=src[:src.index("\nvoid loop() {")]+loop
src=src.replace(chr(92)*2+"n",chr(92)+"n")
src=src.replace("A0_in_calculation=false salinity_calibrated=false", "A0_in_calculation=false value_is_salinity=false")
(sketch/"SalinityMeterCalibrated.ino").write_text(src,encoding="utf-8")
# The calibration endpoints must map exactly before putting the table on device.
for r in (lo,hi):
    predicted=gain*r["index"]/(100-r["index"])+offset
    if abs(predicted-r["reference_percent"])>1e-9: raise ValueError("Endpoint mismatch")
print(json.dumps(model,ensure_ascii=False,indent=2))
