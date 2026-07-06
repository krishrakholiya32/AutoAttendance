# Third-party model attribution

`liveness_model.onnx` (MiniFASNetV2-SE, quantized, ~600KB, ~98% accuracy on
70k+ real/spoof samples) is from
[facenox/face-antispoof-onnx](https://github.com/facenox/face-antispoof-onnx),
licensed under Apache License 2.0 (see `LIVENESS_MODEL_LICENSE.txt` in this
directory). The crop/preprocess/inference logic in
`app/services/liveness_service.py` is ported directly from that repository's
`src/inference/` module.
