/**
 * 人脸识别登录系统 - 主JavaScript文件
 */

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 添加淡入动画效果
    document.querySelectorAll('.card').forEach(function(card) {
        card.classList.add('fade-in');
    });
    
    // 设置当前年份到页脚
    const currentYear = new Date().getFullYear();
    const footerYearElement = document.querySelector('.footer .text-muted');
    if (footerYearElement) {
        footerYearElement.innerHTML = footerYearElement.innerHTML.replace('{{ now.year }}', currentYear);
    }
    
    // 初始化提示工具（Bootstrap Tooltips）
    initializeTooltips();
    
    // 初始化警告消息自动关闭
    initializeAlertDismiss();
});

/**
 * 初始化Bootstrap提示工具
 */
function initializeTooltips() {
    // 检查是否存在Bootstrap的tooltip函数
    if (typeof bootstrap !== 'undefined' && typeof bootstrap.Tooltip !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
}

/**
 * 初始化警告消息自动关闭
 */
function initializeAlertDismiss() {
    // 获取所有警告消息
    const alerts = document.querySelectorAll('.alert');
    
    // 设置5秒后自动关闭
    alerts.forEach(function(alert) {
        setTimeout(function() {
            // 检查是否存在Bootstrap的alert函数
            if (typeof bootstrap !== 'undefined' && typeof bootstrap.Alert !== 'undefined') {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                // 如果Bootstrap未加载，使用普通方式隐藏
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.style.display = 'none';
                }, 500);
            }
        }, 5000);
    });
}

/**
 * 显示加载中状态
 * @param {HTMLElement} button - 按钮元素
 * @param {string} loadingText - 加载中显示的文本
 */
function showLoading(button, loadingText) {
    button.disabled = true;
    button.setAttribute('data-original-text', button.innerHTML);
    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText || '加载中...'}`;
}

/**
 * 恢复按钮状态
 * @param {HTMLElement} button - 按钮元素
 */
function hideLoading(button) {
    button.disabled = false;
    button.innerHTML = button.getAttribute('data-original-text');
}

/**
 * 显示通知消息
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, danger, warning, info)
 */
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 添加到页面
    const container = document.querySelector('.container');
    container.insertBefore(notification, container.firstChild);
    
    // 5秒后自动关闭
    setTimeout(function() {
        notification.classList.remove('show');
        setTimeout(function() {
            notification.remove();
        }, 500);
    }, 5000);
}