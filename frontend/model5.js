document.addEventListener("DOMContentLoaded", function () {
  const BASE_URL = "http://localhost:5000";
  const dropZone1 = document.getElementById("dropZone1");
  const dropZone2 = document.getElementById("dropZone2");
  const fileInput1 = document.getElementById("fileInput1");
  const fileInput2 = document.getElementById("fileInput2");
  const submitBtn = document.getElementById("submitBtn");
  const preview1 = document.getElementById("preview1");
  const preview2 = document.getElementById("preview2");
  const retrievedImages = document.getElementById("retrievedImages");

  let selectedImage = null;
  let preselectedImage = null;
  let selectedAudio = null;
  let preselectedAudio = null;

  function handlePreselectImage(src) {
    preview1.src = src;
    preview1.style.display = "block";
    dropZone1.classList.remove("small");
    dropZone1.classList.add("large");

    fetch(src)
      .then((res) => res.blob())
      .then((blob) => {
        const file = new File([blob], src.split("/").pop(), {
          type: blob.type,
        });
        preselectedImage = file;
        selectedImage = null;
        checkFilesSelected();
      });
  }

  function handlePreselectAudio(audioElement) {
    const audioSrc = audioElement.querySelector("source").src;
    preview2.src = audioSrc;
    preview2.style.display = "block";
    dropZone2.querySelector(".prompt").style.display = "none";

    fetch(audioSrc)
      .then((res) => res.blob())
      .then((blob) => {
        const fileName = audioSrc.split("/").pop();
        preselectedAudio = new File([blob], fileName, { type: "audio/mpeg" });
        selectedAudio = null;
        checkFilesSelected();
      });
  }

  document.querySelectorAll(".preselect-image").forEach((img) => {
    img.addEventListener("click", function () {
      handlePreselectImage(img.src);
    });
  });

  document
    .querySelectorAll(".preselect-audio-container")
    .forEach((container) => {
      container.addEventListener("click", function () {
        container.style.borderColor = "lightblue";
        document.querySelectorAll(".preselect-audio-container").forEach((c) => {
          if (c !== container) c.style.borderColor = "transparent";
        });
        const audio = container.querySelector(".preselect-audio");
        handlePreselectAudio(audio);
      });
    });

  function checkFilesSelected() {
    if (
      (selectedImage || preselectedImage) &&
      (selectedAudio || preselectedAudio)
    ) {
      submitBtn.style.display = "block";
    } else {
      submitBtn.style.display = "none";
    }
  }

  function handleFiles(files, previewElement, isImage = true) {
    const file = files[0];
    if (isImage) {
      selectedImage = file;
      preselectedImage = null;
    } else {
      selectedAudio = file;
      preselectedAudio = null;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
      previewElement.src = e.target.result;
      previewElement.style.display = "block";
      if (isImage) {
        dropZone1.classList.remove("small");
        dropZone1.classList.add("large");
      } else {
        dropZone2.querySelector(".prompt").style.display = "none";
      }
      checkFilesSelected();
    };
    reader.readAsDataURL(file);
  }

  dropZone1.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone1.classList.add("dragover");
  });

  dropZone1.addEventListener("dragleave", function () {
    dropZone1.classList.remove("dragover");
  });

  dropZone1.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone1.classList.remove("dragover");
    const files = e.dataTransfer.files;
    fileInput1.files = files;
    handleFiles(files, preview1);
    checkFilesSelected();
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
    handleFiles(files, preview2, false);
    checkFilesSelected();
  });

  fileInput1.addEventListener("change", function () {
    handleFiles(fileInput1.files, preview1);
    checkFilesSelected();
  });

  fileInput2.addEventListener("change", function () {
    handleFiles(fileInput2.files, preview2, false);
    checkFilesSelected();
  });

  dropZone1.addEventListener("click", function () {
    fileInput1.click();
  });

  dropZone2.addEventListener("click", function () {
    fileInput2.click();
  });

  submitBtn.addEventListener("click", function () {
    const formData = new FormData();
    if (selectedImage) {
      formData.append("image", selectedImage);
    } else if (preselectedImage) {
      formData.append("image", preselectedImage);
    }

    if (selectedAudio) {
      formData.append("audio", selectedAudio);
    } else if (preselectedAudio) {
      formData.append("audio", preselectedAudio);
    }

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

    fetch(`${BASE_URL}/upload`, {
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

                        // 创建新图片元素来检测图片比例
                        const img = new Image();
                        img.onload = function () {
                          const aspectRatio = this.width / this.height;
                          const layout =
                            aspectRatio <= 1 ? "horizontal" : "vertical";

                          retrievedImages.innerHTML = `
                            <div class="retrieved-images-container ${layout}" style="display: flex; 
                                 flex-direction: ${
                                   layout === "horizontal" ? "row" : "column"
                                 }; 
                                 justify-content: center; 
                                 align-items: center;
                                 gap: 40px; 
                                 margin: 0px auto;
                                 width: 100%;">
                              <div style="width: ${
                                layout === "horizontal" ? "45%" : "60%"
                              }; 
                                   max-width: ${
                                     layout === "horizontal" ? "400px" : "500px"
                                   };
                                   min-width: ${
                                     layout === "horizontal" ? "300px" : "300px"
                                   };
                                   padding: 15px; 
                                   background: #fff; 
                                   border-radius: 8px; 
                                   box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                   margin: 0px;">
                                <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">加密图片</div>
                                <img style="width: 100%; display: block; margin: 0px;" src="${BASE_URL}/image_encrypt/${encrypted_image}" alt="加密图片">
                              </div>
                              <div style="width: ${
                                layout === "horizontal" ? "45%" : "60%"
                              }; 
                                   max-width: ${
                                     layout === "horizontal" ? "400px" : "500px"
                                   };
                                   min-width: ${
                                     layout === "horizontal" ? "300px" : "300px"
                                   };
                                   padding: 15px; 
                                   background: #fff; 
                                   border-radius: 8px; 
                                   box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                   margin: 0px;">
                                <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">解密图片</div>
                                <img style="width: 100%; display: block; margin: 0px;" src="${BASE_URL}/image/${decrypted_image}" alt="解密图片">

                              </div>
                            </div>
                          `;
                        };
                        img.src = `${BASE_URL}/image/${decrypted_image}`;
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
