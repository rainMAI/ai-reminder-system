<!-- Auth check script - add to chat-manager.html after <body> tag -->
<script>
// 立即检查登录状态
(function() {
    const token = localStorage.getItem('session_token');
    if (!token) {
        window.location.href = '/static/auth.html';
    }
})();
</script>
