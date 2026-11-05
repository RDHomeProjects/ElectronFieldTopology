# S5-B-006 focused overnight motion

{"utc": "2026-11-05T00:45:38.756334+00:00", "melbourne": "2026-11-05T11:45:38.756334+11:00"}

Status: **complete_pending_review**; complete cases 8/8.

|Case|Status|Milestones|
|---|---|---|
|q1-n101-L16-a0-trilinear|complete|1.0, 2.0, 3.0|
|q1-n101-L16-a0-cubic|complete|1.0, 2.0, 3.0|
|q1-n101-L16-a2-trilinear|complete|1.0, 2.0, 3.0|
|q1-n101-L16-a2-cubic|complete|1.0, 2.0, 3.0|
|q2-n101-L16-a0-trilinear|complete|1.0, 2.0, 3.0|
|q2-n101-L16-a0-cubic|complete|1.0, 2.0, 3.0|
|q2-n101-L16-a2-trilinear|complete|1.0, 2.0, 3.0|
|q2-n101-L16-a2-cubic|complete|1.0, 2.0, 3.0|

|Case / time|Energy drift|Legacy shape error|Tail fraction|Failed scientific checks|
|---|---:|---:|---:|---|
|q1-n101-L16-a0-trilinear / 1.0|4.937e-11|0.014435|0.0030248|shape, tail|
|q1-n101-L16-a0-trilinear / 2.0|1.1259e-10|0.024106|0.0033494|shape, tail|
|q1-n101-L16-a0-trilinear / 3.0|2.0071e-10|0.036136|0.0035882|momentum, shape, tail|
|q1-n101-L16-a0-cubic / 1.0|6.0025e-11|0.011471|0.0030429|shape, speed, tail|
|q1-n101-L16-a0-cubic / 2.0|1.2062e-10|0.021612|0.0033599|shape, speed, tail|
|q1-n101-L16-a0-cubic / 3.0|1.8127e-10|0.034374|0.0035875|momentum, shape, speed, tail|
|q1-n101-L16-a2-trilinear / 1.0|2.3004e-11|0.0084176|0.0030554|tail|
|q1-n101-L16-a2-trilinear / 2.0|5.2887e-11|0.012632|0.0031633|shape, tail|
|q1-n101-L16-a2-trilinear / 3.0|9.7981e-11|0.018655|0.0032568|shape, tail|
|q1-n101-L16-a2-cubic / 1.0|1.4823e-11|0.0057312|0.0030636|tail|
|q1-n101-L16-a2-cubic / 2.0|2.9735e-11|0.01059|0.0031685|shape, tail|
|q1-n101-L16-a2-cubic / 3.0|4.4648e-11|0.016451|0.0032553|shape, tail|
|q2-n101-L16-a0-trilinear / 1.0|6.6856e-10|0.013388|0.0012964|shape, tail|
|q2-n101-L16-a0-trilinear / 2.0|2.8344e-09|0.020634|0.0014805|momentum, shape, tail|
|q2-n101-L16-a0-trilinear / 3.0|5.6108e-09|0.030136|0.0016413|momentum, shape, tail|
|q2-n101-L16-a0-cubic / 1.0|4.3783e-10|0.008966|0.0013024|tail|
|q2-n101-L16-a0-cubic / 2.0|2.124e-09|0.01654|0.0014816|momentum, shape, tail|
|q2-n101-L16-a0-cubic / 3.0|4.3091e-09|0.026031|0.0016346|momentum, shape, speed, tail|
|q2-n101-L16-a2-trilinear / 1.0|1.4945e-11|0.0082875|0.0013322|tail|
|q2-n101-L16-a2-trilinear / 2.0|3.722e-11|0.0099659|0.0013524|tail|
|q2-n101-L16-a2-trilinear / 3.0|7.3076e-11|0.013135|0.0013766|shape, tail|
|q2-n101-L16-a2-cubic / 1.0|1.5734e-12|0.0031534|0.0013346|tail|
|q2-n101-L16-a2-cubic / 2.0|3.1896e-12|0.0059317|0.001353|tail|
|q2-n101-L16-a2-cubic / 3.0|4.8472e-12|0.0089473|0.0013715|tail|

Focused fixed-reflecting-box method comparison; no mesh/domain convergence, isolated stability, charge, quantum spin or electron acceptance.
All raw/projection corrections and scientific failures remain recorded. Wall-sensitive long windows do not establish isolated motion.
