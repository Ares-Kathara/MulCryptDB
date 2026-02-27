const BASE_URL = "http://localhost:5000";

document.getElementById("submitText").addEventListener("click", async () => {
  const textInput = document.querySelector('input[type="text"]');
  const searchText = textInput.value.trim() || textInput.placeholder; // 如果输入为空，使用预设文本

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

  const audioContainer = document.getElementById("audioContainer");
  audioContainer.innerHTML = "";
  const imageContainer = document.getElementById("imageContainer");
  imageContainer.innerHTML = "";

  const response = await fetch(`${BASE_URL}/api/get_text_results`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: searchText }),
  });

  if (!response.ok) {
    console.error("Failed to fetch results:", response.statusText);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  const stream = new ReadableStream({
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
                if (data.startsWith("IMAGE_AUDIO_READY:")) {
                  const [
                    _,
                    encrypted_image,
                    decrypted_image,
                    encrypted_audio,
                    decrypted_audio,
                  ] = data.split(":");

                  const audioWrapper = document.createElement("div");
                  audioWrapper.style =
                    "display: flex; justify-content: center; gap: 40px; margin: 20px 0;";
                  audioWrapper.innerHTML = `
                    <div style="width: 300px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                      <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">加密音频</div>
                      <audio style="width: 100%;" controls controlslist="nodownload noplaybackrate" onplay="this.volume=0.03">
                        <source src="${BASE_URL}/get_music_encrypt/${encrypted_audio}" type="audio/wav">
                      </audio>
                    </div>
                    <div style="width: 300px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                      <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">解密音频</div>
                      <audio style="width: 100%;" controls controlslist="nodownload noplaybackrate">
                        <source src="${BASE_URL}/get_music/${decrypted_audio}" type="audio/wav">
                      </audio>
                    </div>
                  `;
                  audioContainer.appendChild(audioWrapper);

                  const imgWrapper = document.createElement("div");
                  imgWrapper.style =
                    "display: flex; justify-content: center; gap: 40px; margin: 20px 0;";
                  imgWrapper.innerHTML = `
                    <div style="width: 300px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                      <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">加密图片</div>
                      <img style="width: 100%;" src="${BASE_URL}/image_encrypt/${encrypted_image}" alt="加密图片">
                    </div>
                    <div style="width: 300px; padding: 15px; background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                      <div style="margin-bottom: 10px; font-weight: bold; color: #333; text-align: center;">解密图片</div>
                      <img style="width: 100%;" src="${BASE_URL}/image/${decrypted_image}" alt="解密图片">
                    </div>
                  `;
                  imageContainer.appendChild(imgWrapper);
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

  return new Response(stream);

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
      // 显示所有结果，不限制数量
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
