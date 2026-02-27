// 检查登录状态使用 sessionStorage
if (!sessionStorage.getItem("adminLoggedIn")) {
  window.location.href = "./admin_login.html";
}

let allItems = [];
let filteredItems = [];

let state = {
  currentPage: 1,
  totalPages: 1,
  perPage: 30, // 每页显示30个文件
  sortBy: "name",
  sortOrder: "asc",
  fileType: "audio", // 修改默认类型为音频
  searchTerm: "",
  loading: false,
  isInitialLoad: true, // 添加标记初始加载的状态
};

// 修改初始化函数
async function initializeView() {
  // 首先显示欢迎信息
  showWelcomeMessage();

  // 初始化事件监听器
  initializeEventListeners();

  // 默认加载音频文件但不显示
  state.fileType = "audio";
  await preloadFiles();
}

// 修改预加载函数
async function preloadFiles() {
  try {
    const params = new URLSearchParams({
      page: state.currentPage,
      per_page: state.perPage,
      sort_by: state.sortBy,
      sort_order: state.sortOrder,
      type: state.fileType,
      search: state.searchTerm,
    });

    const response = await fetch(`http://localhost:5000/api/files?${params}`);
    const data = await response.json();

    if (!response.ok || data.error) {
      throw new Error(data.error || "Failed to load files");
    }

    // 只更新数据，不渲染界面
    allItems = data.files;
    state.totalPages = data.total_pages || 1;
    console.log("Files preloaded successfully");
  } catch (error) {
    console.error("Preload error:", error);
  }
}

function initializeEventListeners() {
  // 视图切换下拉框
  const viewSelect = document.getElementById("viewSelect");
  if (viewSelect) {
    viewSelect.addEventListener("change", function () {
      renderCurrentView();
    });
  }

  // 修改类型切换下拉框事件
  const typeSelect = document.getElementById("typeSelect");
  if (typeSelect) {
    typeSelect.addEventListener("change", handleTypeChange);
  }

  // 排序控件
  const sortBy = document.getElementById("sortBy");
  const sortOrder = document.getElementById("sortOrder");
  if (sortBy && sortOrder) {
    sortBy.addEventListener("change", updateSort);
    sortOrder.addEventListener("change", updateSort);
  }

  // 退出按钮
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      sessionStorage.removeItem("adminLoggedIn");
      window.location.href = "./admin_login.html";
    });
  }

  // 添加展示按钮事件监听
  const showFilesBtn = document.getElementById("showFilesBtn");
  if (showFilesBtn) {
    showFilesBtn.addEventListener("click", toggleFilesDisplay);
  }
}

function showWelcomeMessage() {
  const adminContent = document.querySelector(".admin-content");
  adminContent.innerHTML = `
    <div class="welcome-message">
      <h2>欢迎使用密联数据库管理系统</h2>
      <div class="quick-guide">
        <p>👈 使用左侧工具栏：</p>
        <ul>
          <li>🔍 搜索特定文件</li>
          <li>📁 选择文件类型（图片/音频）</li>
          <li>🎯 切换显示视图</li>
        </ul>
      </div>
    </div>
  `;
}

// 获取所有文件
async function fetchFiles(resetPage = false) {
  if (resetPage) {
    state.currentPage = 1;
  }

  // 显示加载动画
  showLoader();

  try {
    const params = new URLSearchParams({
      page: state.currentPage,
      per_page: state.perPage,
      sort_by: state.sortBy,
      sort_order: state.sortOrder,
      type: state.fileType,
      search: state.searchTerm,
    });

    console.log("Fetching files with params:", Object.fromEntries(params));

    const response = await fetch(`http://localhost:5000/api/files?${params}`);
    const data = await response.json();

    console.log("Received data:", data);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (data.error) {
      throw new Error(data.error);
    }

    // 确保 data.files 是数组
    if (!Array.isArray(data.files)) {
      console.error("Files data is not an array:", data.files);
      throw new Error("Invalid files data format");
    }

    allItems = data.files;
    state.totalPages = data.total_pages || 1;

    console.log(
      `Loaded ${allItems.length} files, total pages: ${state.totalPages}`
    );

    if (allItems && allItems.length > 0) {
      const adminContent = document.querySelector(".admin-content");
      // 保留排序控件，清除欢迎信息
      const sortControls = adminContent.querySelector(".sort-controls");
      adminContent.innerHTML = "";
      if (sortControls) adminContent.appendChild(sortControls);

      // 重新添加视图容器
      renderCurrentView();
      updatePagination();
    } else {
      showError("没有找到相关文件");
    }
  } catch (error) {
    console.error("Error fetching files:", error);
    showError(`加载文件失败: ${error.message}`);

    // 如果是初始加载失败，显示欢迎信息
    if (state.isInitialLoad) {
      showWelcomeMessage();
    }
  } finally {
    hideLoader();
  }
}

// 添加预加载下一页功能
async function preloadNextPage() {
  const nextPage = state.currentPage + 1;
  if (nextPage > state.totalPages) return;

  const params = new URLSearchParams({
    page: nextPage,
    per_page: state.perPage,
    sort_by: state.sortBy,
    sort_order: state.sortOrder,
    type: state.fileType,
    search: state.searchTerm,
  });

  try {
    await fetch(`http://localhost:5000/api/files?${params}`);
  } catch (error) {
    console.error("Error preloading next page:", error);
  }
}

// 修正加载动画显示
function showLoader() {
  const loader = document.getElementById("loader");
  if (loader) {
    loader.style.display = "block";
    loader.classList.remove("hidden");
  }
}

function hideLoader() {
  const loader = document.getElementById("loader");
  if (loader) {
    loader.style.display = "none";
    loader.classList.add("hidden");
  }
}

function showError(message) {
  const toast = document.getElementById("errorToast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 3000);
}

// 修改渲染视图函数
function renderCurrentView() {
  const adminContent = document.querySelector(".admin-content");
  if (!adminContent) return;

  // 保存当前分页控件
  const existingPagination = document.getElementById("pagination");
  const paginationHTML = existingPagination ? existingPagination.innerHTML : "";

  // 渲染主要内容
  adminContent.innerHTML = `
    <div class="sort-controls">
      <select id="sortBy" onchange="updateSort()">
        <option value="name">按名称排序</option>
        <option value="size">按大小排序</option>
        <option value="date">按日期排序</option>
      </select>
      <select id="sortOrder" onchange="updateSort()">
        <option value="asc">升序</option>
        <option value="desc">降序</option>
      </select>
    </div>
    <div id="gridView" class="grid-view active"></div>
    <div id="tableView" class="table-view" style="display: none;">
      <table>
        <thead>
          <tr>
            <th>文件名</th>
            <th>类型</th>
            <th>大小</th>
            <th>上传时间</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
    <div id="pagination" class="pagination">${paginationHTML}</div>
  `;

  // 更新视图内容
  const viewSelect = document.getElementById("viewSelect");
  const isGridView = viewSelect ? viewSelect.value === "grid" : true;

  const gridView = document.getElementById("gridView");
  const tableView = document.getElementById("tableView");

  if (gridView && tableView) {
    gridView.style.display = isGridView ? "grid" : "none";
    tableView.style.display = isGridView ? "none" : "block";

    if (isGridView) {
      renderGrid();
    } else {
      renderTable();
    }

    // 始终更新分页控件
    updatePagination();
  }
}

// 修改展示按钮的事件处理
function showFiles() {
  showLoader();

  try {
    if (allItems && allItems.length > 0) {
      renderCurrentView();
      updatePagination();
    } else {
      fetchFiles();
    }
  } catch (error) {
    console.error("Error showing files:", error);
    showError("加载文件失败");
  } finally {
    hideLoader();
  }
}

// 修改为切换显示功能
async function toggleFilesDisplay() {
  const adminContent = document.querySelector(".admin-content");
  const isShowingWelcome = adminContent.querySelector(".welcome-message");

  if (isShowingWelcome) {
    // 显示加载动画
    showLoader();
    try {
      // 检查是否还在加载中
      if (state.isLoading) {
        // 等待预加载完成
        await new Promise((resolve) => {
          const checkLoading = setInterval(() => {
            if (!state.isLoading) {
              clearInterval(checkLoading);
              resolve();
            }
          }, 100);
        });
      }

      if (allItems && allItems.length > 0) {
        renderCurrentView();
        updatePagination();
      } else {
        // 如果没有预加载数据，重新获取
        await fetchFiles();
      }
    } catch (error) {
      console.error("Error showing files:", error);
      showError("加载文件失败");
    } finally {
      hideLoader();
    }
  } else {
    showWelcomeMessage();
  }
}

// 渲染网格视图
function renderGrid() {
  const gridView = document.getElementById("gridView");
  if (!allItems || allItems.length === 0) {
    gridView.innerHTML = '<div class="no-results">没有找到相关文件</div>';
    return;
  }

  gridView.innerHTML = allItems
    .map(
      (item) => `
            <div class="grid-item">
                <div class="item-preview" onclick="showPreview('${item.id}')">
                    ${
                      item.type === "image"
                        ? `<img src="http://localhost:5000${item.encrypted_path}" alt="${item.name}" loading="lazy">`
                        : `<div class="audio-player">
                                <div class="audio-icon">
                                    <span>🎵</span>
                                </div>
                               </div>`
                    }
                </div>
                <div class="item-info">
                    <div class="item-name" title="${
                      item.name
                    }">${truncateString(item.name, 20)}</div>
                    <div class="item-size">${formatFileSize(item.size)}</div>
                    <div class="item-type">${
                      item.type === "image" ? "图片" : "音频"
                    }</div>
                </div>
            </div>
        `
    )
    .join("");
}

// 删除原有的 showEncryptedPreview、closeFullscreenPreview 等函数

function truncateString(str, length) {
  return str.length > length ? str.substring(0, length) + "..." : str;
}

function formatDate(timestamp) {
  return new Date(timestamp * 1000).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

// 渲染表格视图
function renderTable() {
  const tableBody = document.getElementById("tableBody");
  tableBody.innerHTML = allItems
    .map(
      (item) => `
    <tr>
        <td class="file-name" onclick="showPreview('${item.id}')">${
        item.name
      }</td>
        <td>${item.type}</td>
        <td>${formatFileSize(item.size)}</td>
        <td>${formatDate(item.date)}</td>
    </tr>
  `
    )
    .join("");
}

// 优化预览模态框显示
async function showPreview(id) {
  try {
    const modal = document.getElementById("previewModal");
    const closeBtn = document.querySelector(".preview-close");
    const item = allItems.find((i) => i.id === id);

    if (!item) return;

    const originalPreview = document.getElementById("originalPreview");
    const encryptedPreview = document.getElementById("encryptedPreview");

    // 显示加载状态
    originalPreview.innerHTML = '<div class="loading">加载中...</div>';
    encryptedPreview.innerHTML = '<div class="loading">加载中...</div>';

    modal.style.display = "block";

    if (item.type === "image") {
      const [origImg, encImg] = await Promise.all([
        loadImage(`http://localhost:5000${item.path}`),
        loadImage(`http://localhost:5000${item.encrypted_path}`),
      ]);

      originalPreview.innerHTML = `<img src="${origImg.src}" alt="原始图片">`;
      encryptedPreview.innerHTML = `<img src="${encImg.src}" alt="加密图片">`;
    } else {
      originalPreview.innerHTML = `
        <audio controls src="http://localhost:5000${item.path}"></audio>
        <p>原始音频</p>
      `;
      encryptedPreview.innerHTML = `
        <audio controls src="http://localhost:5000${item.encrypted_path}" onplay="this.volume=0.03"></audio>
        <p>加密音频</p>
      `;
    }

    // 关闭按钮事件
    closeBtn.onclick = () => (modal.style.display = "none");
    window.onclick = (e) => {
      if (e.target === modal) modal.style.display = "none";
    };
  } catch (error) {
    console.error("Preview error:", error);
    showError("预览加载失败");
  }
}

// 添加图片加载辅助函数
function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const timeoutId = setTimeout(() => {
      reject(new Error("Image load timeout"));
    }, 10000); // 10秒超时

    img.onload = () => {
      clearTimeout(timeoutId);
      resolve(img);
    };

    img.onerror = () => {
      clearTimeout(timeoutId);
      reject(new Error("Image load failed"));
    };

    img.src = src;
  });
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// 修改分页控件更新函数
function updatePagination() {
  const pagination = document.getElementById("pagination");
  if (!pagination) return;

  let paginationHTML = "";

  if (state.totalPages > 0) {
    paginationHTML += `
      <button ${state.currentPage === 1 ? "disabled" : ""} 
        onclick="changePage(${state.currentPage - 1})">上一页</button>
      
      <div class="page-numbers">`;

    // 添加页码按钮
    const maxButtons = 5;
    const startPage = Math.max(
      1,
      state.currentPage - Math.floor(maxButtons / 2)
    );
    const endPage = Math.min(state.totalPages, startPage + maxButtons - 1);

    if (startPage > 1) {
      paginationHTML += `
        <button onclick="changePage(1)">1</button>
        ${startPage > 2 ? "<span>...</span>" : ""}
      `;
    }

    for (let i = startPage; i <= endPage; i++) {
      paginationHTML += `
        <button class="${i === state.currentPage ? "current" : ""}" 
          onclick="changePage(${i})">${i}</button>
      `;
    }

    if (endPage < state.totalPages) {
      paginationHTML += `
        ${endPage < state.totalPages - 1 ? "<span>...</span>" : ""}
        <button onclick="changePage(${state.totalPages})">${
        state.totalPages
      }</button>
      `;
    }

    paginationHTML += `</div>
      <button ${state.currentPage === state.totalPages ? "disabled" : ""} 
        onclick="changePage(${state.currentPage + 1})">下一页</button>
      
      <div class="page-jump">
        <input type="number" id="pageInput" min="1" max="${state.totalPages}" 
          value="${state.currentPage}" />
        <button onclick="jumpToPage()">跳转</button>
      </div>
    `;
  }

  pagination.innerHTML = paginationHTML;
}

// 添加页面跳转功能
function jumpToPage() {
  const pageInput = document.getElementById("pageInput");
  const targetPage = parseInt(pageInput.value);

  if (targetPage && targetPage >= 1 && targetPage <= state.totalPages) {
    changePage(targetPage);
  } else {
    showError("请输入有效的页码");
  }
}

function changePage(page) {
  if (page < 1 || page > state.totalPages) return;
  state.currentPage = page;
  fetchFiles();
}

// 更新排序功能
function updateSort() {
  state.sortBy = document.getElementById("sortBy").value;
  state.sortOrder = document.getElementById("sortOrder").value;
  fetchFiles(true);
}

// 修改类型切换事件
function handleTypeChange() {
  state.fileType = this.value;
  // 切换类型时就开始预加载
  state.isLoading = true; // 标记正在加载
  preloadFiles().then(() => {
    state.isLoading = false;
  });
}

// 修改文档加载事件监听器
document.addEventListener("DOMContentLoaded", () => {
  initializeView();

  const previewModal = document.getElementById("previewModal");
  const closeBtn = document.querySelector(".preview-close");
  if (closeBtn && previewModal) {
    closeBtn.onclick = () => (previewModal.style.display = "none");
    window.onclick = (e) => {
      if (e.target === previewModal) {
        previewModal.style.display = "none";
      }
    };
  }
});

// 优化登出功能
document.getElementById("logoutBtn").addEventListener("click", function () {
  sessionStorage.removeItem("adminLoggedIn");
  localStorage.removeItem("adminLoggedIn"); // 清除旧版本的登录状态
  window.location.href = "./admin_login.html";
});

// 添加分页相关的CSS样式
const style = document.createElement("style");
style.textContent = `
  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    margin-top: 2rem;
  }

  .page-numbers {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .pagination button {
    padding: 0.5rem 1rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    background-color: white;
    cursor: pointer;
  }

  .pagination button.current {
    background-color: #6366f1;
    color: white;
    border-color: #6366f1;
  }

  .pagination button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-jump {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .page-jump input {
    width: 60px;
    padding: 0.3rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
  }
`;
document.head.appendChild(style);
