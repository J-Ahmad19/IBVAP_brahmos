# IBVAP — Algorithm Catalog

Every algorithm below is either lifted directly from one of the four uploaded papers (cited by section/equation) or, where no paper covers a required service, marked **[General CV technique — no uploaded paper]** as you asked. Nothing here is invented without a stated base.

---

## 1. Object Detection — Human Detection & Vehicle Detection services

**Algorithm: YOLO unified detection**
**Service(s):** Human detection & tracking (detection stage) · Vehicle detection & classification (detection stage) · feeds the plate-localization step of ANPR
**Reference:** Redmon, Divvala, Girshick, Farhadi, *"You Only Look Once: Unified, Real-Time Object Detection"*, Section 2 ("Unified Detection"), Eq. 1, Fig. 2–3
**Input:** Single RGB frame, resized to 448×448 (paper's setting; IBVAP prototype uses whatever input size the exported YOLO11n/YOLOv8n model expects)
**Output:** Per-grid-cell bounding boxes `(x, y, w, h)`, objectness confidence, and per-class conditional probabilities

- Divide input image into an `S × S` grid
- → For each grid cell, predict `B` bounding boxes, each with `(x, y, w, h, confidence)`
  - `confidence = Pr(Object) × IOU(pred, truth)` [Eq. before (1)]
- → For each grid cell, predict `C` conditional class probabilities `Pr(Class_i | Object)`
- → At inference, multiply conditional class probability × box confidence to get class-specific confidence score:
  - `Pr(Class_i) × IOU_pred = Pr(Class_i|Object) × Pr(Object) × IOU_pred` [Eq. 1]
- → Apply non-max suppression to collapse duplicate boxes for the same object (paper notes this adds 2–3% mAP, Section 2.3)
- → Return final boxes + class labels + confidence scores

**Notes:** Paper's own network is 24-conv-layer / Fast-YOLO 9-conv-layer; IBVAP's CPU-only build substitutes the same regression formulation implemented in YOLO11n/YOLOv8n (per your earlier architecture decision), exported to OpenVINO/ONNX — the algorithm above (grid regression → confidence fusion → NMS) is unchanged across YOLO versions and is the part directly traceable to this paper.

---

## 2. Multi-Object Tracking — Human & Vehicle Tracking service

**Algorithm: BYTE (association algorithm) / ByteTrack (detector + BYTE)**
**Service(s):** Human detection & tracking (tracking stage) · Vehicle detection & tracking (tracking stage) · supplies track trajectories to the virtual-fence and suspicious-activity services
**Reference:** Zhang et al., *"ByteTrack: Multi-Object Tracking by Associating Every Detection Box"*, Section 3, Algorithm 1
**Input:** Per-frame detection boxes with scores (from the YOLO detector above); a detection score threshold `τ`
**Output:** Set of tracks `T`, each with a persistent identity and bounding box per frame

- Initialize `T ← ∅`
- For each frame `f_k`:
  - Run detector → get all detection boxes `D_k`
  - Split `D_k` into `D_high` (score > τ) and `D_low` (score ≤ τ) [Algorithm 1, lines 3–13]
  - → Predict new location of every existing track using a Kalman filter [line 14–16]
  - **First association:** match `D_high` against all tracks `T` using IoU or Re-ID feature distance similarity + Hungarian algorithm → get `D_remain` (unmatched detections) and `T_remain` (unmatched tracks) [lines 17–19]
  - **Second association:** match `D_low` against `T_remain` using IoU similarity only (motion cue; appearance is unreliable for low-score/occluded boxes) → get `T_re-remain` (still-unmatched tracks) [lines 20–21]
  - → Delete tracks in `T_re-remain` only if lost for more than a set number of frames (paper uses 30) — otherwise keep as "lost" for potential re-match [line 22]
  - → Initialize new tracks from the still-unmatched high-score detections `D_remain` [lines 23–25]
- Return `T`

**Notes:** The paper's central finding — low-confidence boxes (occluded people/vehicles) should be recovered via a *second* motion-only association pass rather than discarded — is the actual mechanism worth implementing; it directly reduces missed detections during partial occlusion at a border fence. ByteTrack itself = YOLOX detector + BYTE; IBVAP substitutes its own CPU-exported detector but keeps BYTE unchanged.

---

## 3. Face Recognition — Face Detection & Watchlist Matching service

**Algorithm: ArcFace (Additive Angular Margin Loss) embedding + matching**
**Service(s):** Face detection & recognition (watchlist matching stage)
**Reference:** Deng, Guo, Yang, Xue, Kotsia, Zafeiriou, *"ArcFace: Additive Angular Margin Loss for Deep Face Recognition"*, Section 3.1, Eq. 1–3, Fig. 2; verification protocol in Section 4.1
**Input:** Aligned face crop, `112×112`, from 5 facial landmark points (paper's own preprocessing, Section 4.1)
**Output:** A 512-D embedding vector per face; a match/no-match decision against a watchlist

*Embedding computation (what the pretrained network does per face):*
- Extract deep feature `x_i ∈ R^512` from the aligned face crop via the CNN backbone
- → L2-normalize the feature `x_i` and each class-center weight `W_j`, so predictions depend only on the **angle** between them, not magnitude [Section 3.1, following Eq. 1]
- → Compute `θ_yi = arccos(W_yi^T x_i)`, the angle between the feature and its target class center
- → Add an additive angular margin `m` to the target angle: `cos(θ_yi + m)` [Eq. 3] — this step only applies during training of the embedding network, not at inference
- → (Training only) rescale by `s` and pass through softmax + cross-entropy to update the network

*Watchlist matching (what IBVAP runs at inference, derived directly from the paper's own verification protocol, Section 4.1):*
- Compute embedding `x_probe` for the detected face (same pretrained network, no margin/softmax head at inference — embedding only)
- → For each watchlist entry, retrieve its stored embedding `x_watchlist` (already computed once at enrollment)
- → Compute cosine similarity `cos(θ) = x_probe · x_watchlist`
- → If similarity ≥ threshold → raise a `face_match` event with the similarity score attached; always route to human review, never auto-act
- → If below threshold, discard (do not retain the probe embedding beyond the immediate check, per the privacy note in your earlier architecture doc)

**Notes:** Sub-center ArcFace (Section 3.2 of the paper) exists to make *training* robust to noisy web-scraped face datasets — it is not relevant to IBVAP's inference-only deployment on a pretrained model, so it's omitted here rather than force-fit.

---

## 4. Suspicious Activity / Anomaly Detection — Suspicious Activity Detection service

All three come from B. Ravi Kiran, Thomas, Parakkal, *"An Overview of Deep Learning Based Methods for Unsupervised and Semi-Supervised Anomaly Detection in Videos"*. All three assume training video contains **only normal behavior** (no labeled anomalies) — the "semi-supervised" setup the paper defines in Section 1.1.

### 4a. Reconstruction-based (Convolutional Autoencoder)
**Reference:** Section 3.4, Eq. 7–8 (Spatio-Temporal Stacked Frame AutoEncoder, citing Hasan et al. 2016)
**Input:** A stacked cuboid of `p` consecutive frames, each channel = one time step
**Output:** Per-frame anomaly/regularity score

- Stack `p` consecutive frames into a tensor `x_i ∈ R^(r×c×p)`
- → Train a convolutional autoencoder to reconstruct `x_i` **only on normal-behavior training video** (no anomalies present), minimizing `L(W) = (1/2N)Σ‖x_i − f_W(x_i)‖² + ν‖W‖²` [Eq. 7]
- → At inference, compute the reconstruction error map `E_t = |X_t − X̂_t|`
- → Compute the temporal regularity score `s(t) = 1 − [Σ(E_t) − min(E_t)] / max(E_t)` [Eq. 8]
- → Threshold: `s(t)` below a set value ⇒ flag frame/region as anomalous (e.g., loitering, unusual object)

### 4b. Predictive-based (Convolutional LSTM)
**Reference:** Section 4.2, Eq. 10, Fig. 6, citing Xingjian et al. 2015 (ConvLSTM) and the composite reconstruction+prediction model of Srivastava et al. 2015 (Section 4.1, Fig. 5)
**Input:** Sequence of `p` past frames
**Output:** Predicted next frame + prediction-error anomaly score

- Feed the past `p` frames into a ConvLSTM encoder, which compresses the sequence into a hidden state tensor while preserving spatial correlation (unlike a fully-connected LSTM) [Eq. 10 gate equations]
- → A forecasting/decoder network unfolds the hidden state to predict the next frame(s)
- → Compute the prediction error between predicted and actual next frame
- → Threshold the error: high prediction error ⇒ the observed motion pattern deviates from learned "normal" behavior ⇒ flag as suspicious

### 4c. Generative-based (Variational Autoencoder reconstruction probability)
**Reference:** Section 5.2–5.3, Eq. 15–16, citing An & Cho 2015 and the original VAE (Kingma & Welling 2014)
**Input:** Single frame (or frame patch)
**Output:** Reconstruction-probability anomaly score

- Encode input `x` via the probabilistic encoder `q_φ(z|x)` to obtain a mean vector `μ_z` and standard-deviation vector `σ_z`
- → Sample `L` latent vectors `z^(i,l) ~ N(μ_z, σ_z)`
- → Decode each sampled `z^(i,l)` through the probabilistic decoder to get reconstructed distribution parameters `μ̂_x^(i,l), σ̂_x^(i,l)`
- → Compute the reconstruction probability, averaged over the `L` samples: `P_recon(x) = (1/L) Σ p_θ(x | μ̂_x^(i,l), σ̂_x^(i,l))` [Eq. 16]
- → Threshold: low `P_recon(x)` ⇒ the sample is poorly explained by the "normal" distribution ⇒ flag as anomalous

**Which to actually run on CPU:** the paper's own benchmark (Table 1–2, Section 6.2) found the reconstruction-based and VAE approaches performed comparably to a PCA-on-optical-flow baseline and were the cheapest to run; the ConvLSTM family was the most compute-hungry of the three in their own experiments. That trade-off is worth weighing against your CPU-only constraint when you get to implementation — flagging it here rather than deciding it for you, since you asked for all three as options.

---

## 5. General CV Techniques — services with no uploaded paper

These four services from the problem statement aren't covered by any of the four papers you gave me. Standard, well-established techniques, labeled as such rather than dressed up as paper-derived.

### 5a. ANPR — Plate Localization + Recognition
**[General CV technique — no uploaded paper; standard two-stage ANPR pipeline]**
**Service:** Automatic Number Plate Recognition
**Input:** Vehicle bounding box crop (output of the YOLO detector, §1 above)
**Output:** Plate text string + confidence

- Crop the vehicle bounding box region from the frame
- → Run a plate-localizer (a small object detector, same detection paradigm as §1, retrained on a "license plate" class) to get a tight plate bounding box
- → Crop and rectify the plate region
- → Run a text-recognition network (CRNN/CTC-style, e.g. PaddleOCR's recognition head) over the cropped plate to output a raw character sequence
- → Post-process: apply a regex/format validator against the expected plate schema (e.g., state code + RTO code + series + number for Indian plates)
- → Apply known OCR-confusion correction rules (0↔O, 1↔I, 8↔B) guided by the position expected to be alphabetic vs numeric in the schema
- → Output validated plate string + confidence; cross-reference against the watchlist table

### 5b. Virtual Fence / Intrusion Detection
**[General CV technique — no uploaded paper; standard point-in-polygon geofencing]**
**Service:** Virtual fence intrusion detection
**Input:** A per-camera polygon (list of vertex coordinates, drawn once at setup) + a track's bounding box per frame (from §2 above)
**Output:** Boolean crossing event per track

- Define the fence as a polygon (or line) in the camera's pixel coordinate space, stored once per camera
- → For each tracked object, compute its ground-contact reference point (typically the bottom-center of its bounding box)
- → Test whether that point lies inside or outside the polygon (point-in-polygon test, e.g. ray-casting)
- → Maintain a boolean inside/outside state per track ID, updated every processed frame
- → When the state flips (outside→inside, or the configured direction), require the new state to hold for `N` consecutive frames before raising an event (debounce, to suppress single-frame jitter/noise)
- → On confirmed crossing, raise a `fence_crossing` event tagged with direction, track ID, and camera ID

### 5c. Night-Time / Low-Light Preprocessing
**[General CV technique — no uploaded paper; CLAHE is a classical image-processing algorithm, not from any of the four uploaded papers]**
**Service:** Night-time movement detection
**Input:** A single low-light frame
**Output:** A contrast-enhanced frame for the detector, or a fallback "unclassified movement" flag

- Convert the frame to a luminance-separable color space (e.g. LAB)
- → Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) to the luminance channel only, to recover contrast without amplifying sensor noise the way global histogram equalization would
- → Recombine channels and convert back to RGB
- → Feed the enhanced frame into the standard detection pipeline (§1)
- → **Fallback path:** if the detector's confidence stays below threshold on a frame with significant pixel-level change, compute a frame-differencing motion heatmap (`|frame_t − frame_t-1|` thresholded) over the relevant ROI
- → If motion exceeds a set area/intensity threshold with no confident detection, raise a lower-confidence `unclassified_movement` event rather than dropping the frame silently

### 5d. Event Aggregation & Alerting
**[General technique — no uploaded paper; standard rule-based event-severity pattern, not a CV algorithm]**
**Service:** Real-time alert generation and event logging
**Input:** Normalized `Event` objects emitted by every algorithm above (type, camera_id, timestamp, track_id, confidence)
**Output:** A severity-tagged, routed alert

- Receive an `Event` object from any upstream module (detection/tracking/face/ANPR/fence/anomaly)
- → Look up the severity rule for that event type (e.g., `face_match` against a critical watchlist = high severity; single `loitering` event = low severity)
- → Attach severity + a snapshot/clip reference to the event
- → Write the event immutably to the event store (append-only)
- → Fan out to the relevant channel(s): live dashboard (WebSocket), external C2 system (webhook), duty-officer notification — based on severity

---

## Summary Table

| Service | Algorithm | Source |
|---|---|---|
| Human detection & tracking (detect) | YOLO unified detection | Redmon et al., §2 |
| Vehicle detection & classification (detect) | YOLO unified detection | Redmon et al., §2 |
| Human/vehicle tracking | BYTE association | Zhang et al., Algorithm 1 |
| Face detection & recognition | ArcFace embedding + cosine matching | Deng et al., §3.1 / §4.1 |
| Suspicious activity detection | Reconstruction autoencoder | Ravi Kiran et al., §3.4 |
| Suspicious activity detection | ConvLSTM predictive | Ravi Kiran et al., §4.2 |
| Suspicious activity detection | VAE reconstruction probability | Ravi Kiran et al., §5.2–5.3 |
| ANPR | Plate localization + OCR | General technique |
| Virtual fence intrusion | Point-in-polygon geofencing | General technique |
| Night-time movement detection | CLAHE + motion-diff fallback | General technique |
| Real-time alerting & logging | Rule-based event severity routing | General technique |
