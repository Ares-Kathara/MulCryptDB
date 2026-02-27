document.addEventListener("DOMContentLoaded", function () {
  const BASE_URL = "http://localhost:5000";
  const dropZone2 = document.getElementById("dropZone2");
  const fileInput2 = document.getElementById("fileInput2");
  const textInput = document.getElementById("textInput");
  const submitBtn = document.getElementById("submitBtn");
  const preview2 = document.getElementById("preview2");
  const retrievedImages = document.getElementById("retrievedImages");

  let selectedAudio = null;
  let preselectedAudio = null;

  // 确保submitBtn初始隐藏
  submitBtn.style.display = "none";

  function checkSubmitCondition() {
    // 只要有音频就显示检索按钮
    if (selectedAudio || preselectedAudio) {
      submitBtn.style.display = "block";
    } else {
      submitBtn.style.display = "none";
    }
  }

  function handleFiles(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      preview2.src = e.target.result;
      preview2.style.display = "block";
      dropZone2.querySelector(".prompt").style.display = "none";
      checkSubmitCondition();
    };
    reader.readAsDataURL(file);
  }

  function handlePreselectAudio(audioElement) {
    const audioSrc = audioElement.querySelector("source").src;
    preview2.src = audioSrc;
    preview2.style.display = "block";
    dropZone2.querySelector(".prompt").style.display = "none";

    // 立即创建一个临时的空 File 对象，使检查条件能够立即生效
    preselectedAudio = new File([""], audioSrc.split("/").pop(), {
      type: "audio/mpeg",
    });
    selectedAudio = null;
    checkSubmitCondition();

    // 然后异步获取实际的音频文件
    fetch(audioSrc)
      .then((res) => res.blob())
      .then((blob) => {
        preselectedAudio = new File([blob], audioSrc.split("/").pop(), {
          type: "audio/mpeg",
        });
        checkSubmitCondition();
      });
  }

  document
    .querySelectorAll(".preselect-audio-container")
    .forEach((container) => {
      container.addEventListener("click", function () {
        const audio = container.querySelector(".preselect-audio");
        handlePreselectAudio(audio);
      });
    });

  dropZone2.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone2.classList.add("dragover");
  });

  dropZone2.addEventListener("dragleave", function () {
    dropZone2.classList.remove("dragover");
  });

  dropZone2.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone2.classList.remove("dragover");
    const files = e.dataTransfer.files;
    fileInput2.files = files;
    selectedAudio = files[0];
    preselectedAudio = null;
    handleFiles(selectedAudio);
  });

  fileInput2.addEventListener("change", function () {
    selectedAudio = fileInput2.files[0];
    preselectedAudio = null;
    handleFiles(selectedAudio);
  });

  dropZone2.addEventListener("click", function () {
    fileInput2.click();
  });

  textInput.addEventListener("input", checkSubmitCondition);

  submitBtn.addEventListener("click", function () {
    const formData = new FormData();
    if (preselectedAudio) {
      formData.append("audio", preselectedAudio);
    } else if (selectedAudio) {
      formData.append("audio", selectedAudio);
    }
    // 如果文本框为空，使用预设文本
    const searchText = textInput.value.trim() || "飞机";
    formData.append("text", searchText);

    // 初始化状态对象
    const state = {
      currentR: null,
      performance: {},
      tokens: {},
      searchResults: [],
      matchedItem: {},
    };

    // 重置所有卡片内容
    document.getElementById("performance-metrics").innerHTML = "";
    document.getElementById("token-tree").innerHTML = "";
    document.getElementById("search-results").innerHTML = "";

    retrievedImages.innerHTML = "";

    fetch(`${BASE_URL}/upload_t_a`, {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        return new ReadableStream({
          start(controller) {
            function push() {
              reader
                .read()
                .then(({ done, value }) => {
                  if (done) {
                    controller.close();
                    return;
                  }

                  const text = decoder.decode(value, { stream: true });
                  const lines = text.split("\n");

                  lines.forEach((line) => {
                    if (line.startsWith("data: ")) {
                      const data = line.slice(6);
                      if (data.startsWith("IMAGE_READY:")) {
                        const [_, encrypted_image, decrypted_image] =
                          data.split(":");
                        retrievedImages.innerHTML = `
                          <div style="display: flex; justify-content: center; gap: 40px; margin: 0px 0;">
                            <div style="width: 300px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">加密图片</div>  
                                <img style="width: 100%;" src="${BASE_URL}/image_encrypt/${encrypted_image}" alt="加密图片">
                            </div>
                            <div style="width: 300px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                              <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">解密图片</div>
                              <img style="width: 100%;" src="${BASE_URL}/image/${decrypted_image}" alt="解密图片">
                            </div>
                          </div>
                        `;
                      } else {
                        processLogLine(data, state);
                      }
                    }
                  });

                  controller.enqueue(value);
                  push();
                })
                .catch((error) => {
                  console.error("Error:", error);
                  controller.error(error);
                });
            }
            push();
          },
        });
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  });

  // 日志处理函数
  function processLogLine(line, state) {
    if (line.startsWith("推理所需时间")) {
      state.performance.inference = parseFloat(line.split(":")[1].trim());
      updatePerformance(state);
    } else if (line.startsWith("生成token所需时间")) {
      state.performance.tokenGen = parseFloat(line.split(":")[1].trim());
      updatePerformance(state);
    } else if (line.startsWith("r=")) {
      const rLevel = line.match(/r=(\d+)/)[1];
      state.currentR = rLevel;
      state.tokens[rLevel] = [];
    } else if (line.startsWith("token :")) {
      const tokens = line.split(":")[1].trim().split(", ");
      if (state.currentR !== null) {
        state.tokens[state.currentR].push(tokens);
        updateTokenTree(state);
      }
    } else if (line.startsWith("返回加密检索结果")) {
      state.searchResults = [];
      updateSearchResults(state);
    } else if (line.startsWith("检索所需时间")) {
      state.performance.search = parseFloat(line.split(":")[1].trim());
      updatePerformance(state);
    } else if (line.startsWith("检索结果数量")) {
      state.searchResults.length = parseFloat(line.split(":")[1].trim());
      updatePerformance(state);
    } else if (/^[a-f0-9]{32}$/.test(line.trim())) {
      state.searchResults.push(line.trim());
      updateSearchResults(state);
    }
  }

  // 更新UI函数
  function updatePerformance(state) {
    if (
      state.performance.inference ||
      state.performance.tokenGen ||
      state.performance.search
    ) {
      document.querySelector("#performance-card h3").style.display = "block";
      const metrics = [
        `⚡ 特征提取: ${state.performance.inference || "-"}s`,
        `🔑 Token生成: ${state.performance.tokenGen || "-"}s`,
        `⏱️ 检索耗时: ${state.performance.search || "-"}s`,
        `📊 结果数量: ${state.searchResults.length}`,
      ];
      document.getElementById(
        "performance-metrics"
      ).innerHTML = `${metrics[0]} &nbsp;&nbsp;&nbsp;&nbsp; ${metrics[1]}&nbsp;&nbsp;&nbsp;&nbsp;${metrics[2]} &nbsp;&nbsp;&nbsp;&nbsp; ${metrics[3]}`;
    }
  }

  function updateTokenTree(state) {
    const container = document.getElementById("token-tree");
    let html = "";

    if (Object.keys(state.tokens).length > 0) {
      document.querySelector("#encryption-card h3").style.display = "block";
      Object.entries(state.tokens).forEach(([rLevel, tokens]) => {
        html += `<div class="r-level">🔗 r=${rLevel}</div>`;
        tokens.forEach(([t1, t2]) => {
          html += `
          <div class="token-pair">
            <div class="token">${shortenHash(t1)}</div>
            <div class="token">${shortenHash(t2)}</div>
          </div>`;
        });
      });
    }

    container.innerHTML = html;
  }

  function updateSearchResults(state) {
    const container = document.getElementById("search-results");
    if (state.searchResults.length > 0) {
      document.querySelector("#results-card h3").style.display = "block";
      const items = state.searchResults
        .map((h) => `<div class="hash-item">${h}</div>`)
        .join("");

      container.innerHTML = items;
    }
  }

  function shortenHash(hash) {
    // 不再截断，直接返回完整哈希值
    return hash || "";
  }

  function shortenPath(path, max = 30) {
    return path?.length > max ? `...${path.slice(-max)}` : path;
  }
});
