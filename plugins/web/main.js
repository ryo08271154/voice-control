import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin } from "@pixiv/three-vrm";

let renderer, camera, scene, controls, currentVrm, mixer, humanoid;
let isLipSyncing = false;
const lipSyncDuration = 30000;
let lipSyncStartTime = 0;
let naturalPose = null;

// まばたき関連の変数
let blinkTimer = 0;
let nextBlinkTime = 3;

// WebSocket関連の変数
let ws = null;
let currentExpression = null;
let expressionValue = 0;

const init = () => {
  renderer = new THREE.WebGLRenderer({
    canvas: document.querySelector("canvas"),
    antialias: true,
  });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  );
  camera.position.set(0, 1.3, 0.5);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.3, 0);
  controls.update();

  const light = new THREE.DirectionalLight(0xffffff);
  light.position.set(1, 1, 1).normalize();
  scene.add(light);

  naturalPose = {
    rightUpperArm: {
      rotation: [0.0, 0.0, 0.6088, 0.7934],
    },
    leftUpperArm: {
      rotation: [0.0, 0.0, -0.6088, 0.7934],
    },
    rightLowerArm: {
      rotation: [0.0, 0.0, 0.0, 1.0],
    },
    leftLowerArm: {
      rotation: [0.0, 0.0, 0.0, 1.0],
    },
  };

  const loader = new GLTFLoader();

  loader.register((parser) => {
    return new VRMLoaderPlugin(parser);
  });

  loader.load(
    "models/model.vrm",
    (gltf) => {
      const vrm = gltf.userData.vrm;
      currentVrm = vrm;
      scene.add(vrm.scene);
      humanoid = vrm.humanoid;

      // 利用可能な表情名を出力
      const expressions = vrm.expressionManager.expressionMap;
      console.log("VRM loaded. Natural pose applied.");
      console.log("利用可能な表情:", Object.keys(expressions));
    },
    (progress) =>
      console.log(
        "Loading model...",
        100.0 * (progress.loaded / progress.total),
        "%"
      ),
    (error) => console.error(error)
  );

  document.body.appendChild(renderer.domElement);
  initWebSocket();
};

function onResize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", onResize);

const clock = new THREE.Clock();
clock.start();

function tick() {
  const deltaTime = clock.getDelta();

  if (currentVrm) {
    humanoid.setNormalizedPose(naturalPose);

    blinkTimer += deltaTime;

    if (blinkTimer >= nextBlinkTime) {
      const blinkPhase = (blinkTimer - nextBlinkTime) / 0.15;

      if (blinkPhase < 1.0) {
        // まばたき中: サイン波で滑らかに開閉
        const blinkValue = Math.sin(blinkPhase * Math.PI);
        currentVrm.expressionManager.setValue("blink", blinkValue);
      } else {
        // まばたき終了: 次のまばたきまでの時間を設定
        currentVrm.expressionManager.setValue("blink", 0);
        blinkTimer = 0;
        nextBlinkTime = 2 + Math.random() * 4; // 2~6秒後に次のまばたき
      }
    } else {
      currentVrm.expressionManager.setValue("blink", 0);
    }

    if (
      currentExpression &&
      currentExpression !== "aa" &&
      currentExpression !== "blink"
    ) {
      currentVrm.expressionManager.setValue(currentExpression, expressionValue);
    }

    if (isLipSyncing) {
      const elapsedTime = (Date.now() - lipSyncStartTime) / 1000;
      const lipOpen = (Math.sin(elapsedTime * 20.0) + 1.0) / 2.0;
      currentVrm.expressionManager.setValue("aa", lipOpen);

      if (Date.now() - lipSyncStartTime > lipSyncDuration) {
        isLipSyncing = false;
      }
    } else {
      currentVrm.expressionManager.setValue("aa", 0);
    }

    currentVrm.expressionManager.update();
    currentVrm.update(deltaTime);
  }
  if (mixer) mixer.update(clock.getDelta());
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

init();
tick();

function initWebSocket() {
  ws = new WebSocket("ws://localhost:8765");

  ws.onopen = () => {
    console.log("WebSocket接続が確立されました");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    } catch (error) {
      console.error("WebSocketメッセージの解析エラー:", error);
    }
  };

  ws.onerror = (error) => {
    console.error("WebSocketエラー:", error);
  };

  ws.onclose = () => {
    console.log("WebSocket接続が切断されました。5秒後に再接続します...");
    setTimeout(initWebSocket, 5000); // 5秒後に再接続
  };
}

function handleWebSocketMessage(data) {
  if (data.command === "startLipSync") {
    startLipSync();
  } else if (data.command === "stopLipSync") {
    stopLipSync();
  } else if (data.command === "setExpression") {
    setExpression(data.expression, data.value || 1.0);
  } else if (data.command === "resetExpression") {
    resetExpression();
  }
}

function startLipSync() {
  isLipSyncing = true;
  lipSyncStartTime = Date.now();
  console.log("口パク開始");
}

function stopLipSync() {
  isLipSyncing = false;
  console.log("口パク停止");
}

function setExpression(expressionName, value = 1.0) {
  if (!currentVrm) {
    console.warn("VRMモデルがまだロードされていません");
    return;
  }

  if (
    !expressionName ||
    expressionName === "" ||
    expressionName === "neutral"
  ) {
    resetExpression();
    return;
  }

  if (currentExpression && currentExpression !== expressionName) {
    if (currentExpression !== "aa" && currentExpression !== "blink") {
      currentVrm.expressionManager.setValue(currentExpression, 0);
    }
  }

  currentExpression = expressionName;
  expressionValue = Math.max(0, Math.min(1, value)); // 0.0 ~ 1.0の範囲に制限

  console.log(`表情を設定: ${expressionName} (強さ: ${expressionValue})`);
}

function resetExpression() {
  if (!currentVrm) {
    return;
  }

  if (
    currentExpression &&
    currentExpression !== "aa" &&
    currentExpression !== "blink"
  ) {
    currentVrm.expressionManager.setValue(currentExpression, 0);
  }

  currentExpression = null;
  expressionValue = 0;

  console.log("表情をリセットしました");
}
