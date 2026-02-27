document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("loginForm");
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  const rememberMeCheckbox = document.getElementById("rememberMe");
  const errorMessage = document.getElementById("error-message");

  // 检查是否存在已保存的用户名和密码
  if (localStorage.getItem("username")) {
    usernameInput.value = localStorage.getItem("username");
    passwordInput.value = localStorage.getItem("password");
    rememberMeCheckbox.checked = true;
  }

  loginForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    const rememberMe = rememberMeCheckbox.checked;

    // 添加简单的输入验证
    if (!username || !password) {
      showError("用户名和密码不能为空");
      return;
    }

    // 模拟验证 (实际应该由后端处理)
    if (username === "admin" && password === "admin123") {
      try {
        // 使用 sessionStorage 存储登录状态
        sessionStorage.setItem("adminLoggedIn", "true");

        // 只有选择记住密码时才使用 localStorage
        if (rememberMe) {
          localStorage.setItem("username", username);
          localStorage.setItem("password", password);
        } else {
          localStorage.removeItem("username");
          localStorage.removeItem("password");
        }

        window.location.href = "./admin_dashboard.html";
      } catch (error) {
        showError("登录过程中出现错误");
        console.error("Login error:", error);
      }
    } else {
      showError("用户名或密码错误");
      passwordInput.value = ""; // 清空密码输入
    }
  });

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove("hidden");
    setTimeout(() => {
      errorMessage.classList.add("hidden");
    }, 3000);
  }
});
