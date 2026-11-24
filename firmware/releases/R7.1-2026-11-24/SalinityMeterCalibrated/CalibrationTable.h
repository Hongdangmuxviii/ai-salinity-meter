#pragma once
// Comparative prototype table; independent accuracy and temperature correction are not validated.
constexpr char calibrationId[] = "REF_4P_20261124_V2";
constexpr unsigned int calibrationPointCount = 4;
constexpr double calibrationIndices[4] = {95.2145288162, 96.21234, 97.671489063, 99.42491};
constexpr double calibrationPercents[4] = {0.5, 0.6, 1.1, 2};
constexpr double calibrationTemperatures[4] = {19.25, 20.31, 19.25, 21.56};
constexpr double calibrationIndexLow = calibrationIndices[0];
constexpr double calibrationIndexHigh = calibrationIndices[3];

