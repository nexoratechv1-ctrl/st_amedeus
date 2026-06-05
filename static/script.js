// static/script.js
// Additional JS for general interactions and API handlers
window.addEventListener('load', () => {
    // Dark mode toggle (optional upgrade) - but default dark is on
    console.log("School Management System - Premium Edition");
});
// Any global functions such as logout can be added
function logout() { localStorage.removeItem('token'); window.location.href='/'; }
