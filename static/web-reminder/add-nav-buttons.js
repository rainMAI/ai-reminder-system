// 为web-reminder添加导航按钮
(function() {
    // 等待DOM加载完成
    const addButtons = () => {
        // 修改标题
        const titleElement = document.querySelector('title');
        if (titleElement && titleElement.textContent.includes('ESP32 提醒管理系统')) {
            titleElement.textContent = '提醒管理';
        }

        // 修改页面中的标题文本
        const updateText = () => {
            // 查找所有包含ESP32 提醒管理系统的元素
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) {
                    const text = el.childNodes[0].textContent;
                    if (text && text.includes('ESP32 提醒管理系统')) {
                        el.childNodes[0].textContent = text.replace('ESP32 提醒管理系统', '提醒管理');
                    }
                }
            });

            // 隐藏添加设备按钮（通过文本内容查找）
            const buttons = document.querySelectorAll('button, .btn, [role="button"]');
            buttons.forEach(btn => {
                if (btn.textContent.includes('添加设备')) {
                    btn.style.display = 'none';
                }
            });
        };

        // 立即执行一次
        updateText();
        
        // 定期检查（防止动态加载的内容）
        const observer = new MutationObserver(() => {
            updateText();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // 查找header元素
        const header = document.querySelector('.header-content') || document.querySelector('.header');

        if (!header) {
            console.log('Header not found, retrying...');
            setTimeout(addButtons, 500);
            return;
        }

        // 检查是否已添加按钮
        if (document.querySelector('.nav-back-btn') || document.querySelector('.nav-logout-btn')) {
            return;
        }

        // 创建按钮容器
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'nav-button-container';
        buttonContainer.style.cssText = `
            display: flex;
            gap: 10px;
            margin-left: 20px;
        `;

        // 创建返回门户按钮
        const backBtn = document.createElement('button');
        backBtn.className = 'nav-back-btn';
        backBtn.textContent = '← 返回门户';
        backBtn.style.cssText = `
            padding: 10px 20px;
            background: #95a5a6;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
        `;
        backBtn.onmouseenter = () => { backBtn.style.background = '#7f8c8d'; };
        backBtn.onmouseleave = () => { backBtn.style.background = '#95a5a6'; };
        backBtn.onclick = () => {
            window.location.href = '/static/portal.html';
        };

        // 创建退出登录按钮
        const logoutBtn = document.createElement('button');
        logoutBtn.className = 'nav-logout-btn';
        logoutBtn.textContent = '退出登录';
        logoutBtn.style.cssText = `
            padding: 10px 20px;
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
        `;
        logoutBtn.onmouseenter = () => { logoutBtn.style.background = '#c0392b'; };
        logoutBtn.onmouseleave = () => { logoutBtn.style.background = '#e74c3c'; };
        logoutBtn.onclick = async () => {
            if (!confirm('确定要退出登录吗？')) return;

            const token = localStorage.getItem('session_token');
            const API_BASE = window.location.protocol + '//' + window.location.hostname + ':8081/api';

            try {
                await fetch(`${API_BASE}/auth/logout`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
            } catch (e) {}

            localStorage.removeItem('session_token');
            localStorage.removeItem('username');
            localStorage.removeItem('user_id');
            window.location.href = '/static/auth.html';
        };

        // 添加按钮到容器
        buttonContainer.appendChild(backBtn);
        buttonContainer.appendChild(logoutBtn);

        // 添加到header
        header.appendChild(buttonContainer);

        console.log('Navigation buttons added successfully!');
    };

    // DOM加载完成后添加按钮
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addButtons);
    } else {
        addButtons();
    }
})();
