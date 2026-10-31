/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./src/js/modules/functions.js"
/*!*************************************!*\
  !*** ./src/js/modules/functions.js ***!
  \*************************************/
(__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   isWebp: () => (/* binding */ isWebp)
/* harmony export */ });
function isWebp() {
    function testWebp(callback) {
        let webP = new Image();
        webP.onload = webP.onerror = function () {
            callback(webP.height == 2);
        }
        webP.src = "data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA";
    }
    testWebp(function (support) {
        let className = support === true ? 'webp' : 'no-webp';
        document.documentElement.classList.add(className);
    })
}

/***/ },

/***/ "./src/js/modules/header.js"
/*!**********************************!*\
  !*** ./src/js/modules/header.js ***!
  \**********************************/
(__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) {

__webpack_require__.r(__webpack_exports__);
document.addEventListener('DOMContentLoaded', () => {
    const profileBtn = document.querySelector('#profileBtn');
    const menu = document.querySelector('.profile-menu');
    const exitBtn = document.querySelector('._exit');

    if (profileBtn && menu) {
        profileBtn.addEventListener('click', function(e) {
            if (e.target.closest('.profile-menu__link')) return;

            e.preventDefault();
            e.stopPropagation();

            menu.classList.toggle('_active');
            console.log('Меню переключено');
        });

        document.addEventListener('click', (e) => {
            if (!profileBtn.contains(e.target)) {
                menu.classList.remove('_active');
            }
        });
    }

    if (exitBtn) {
        exitBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Отменяем стандартный переход по href="#"

            // 1. Очищаем сохраненные данные сессии
            localStorage.removeItem('token');
            localStorage.removeItem('userName');
            localStorage.removeItem('userId');

            // 2. Перекидываем на страницу логина
            window.location.href = '/index.html';
        });
    }
});

/***/ },

/***/ "./src/js/modules/login.js"
/*!*********************************!*\
  !*** ./src/js/modules/login.js ***!
  \*********************************/
(__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) {

__webpack_require__.r(__webpack_exports__);
const loginForm = document.querySelector('.login__form');

if (loginForm) {
    const usernameInput = loginForm.querySelector('input[name="username"]');
    const passwordInput = document.querySelector('#passwordInput');
    const submitBtn = loginForm.querySelector('.login__submit');
    const submitIcon = submitBtn.querySelector('img');
    const toggleButton = document.querySelector('.login__toggle');
    const eyeIcon = toggleButton.querySelector('img');
    const errorText = document.querySelector('#passwordError');

    // Проверка заполненности полей (оставляем как было у коллеги)
    function checkInputs() {
        const isUsernameFilled = usernameInput.value.trim() !== '';
        const isPasswordFilled = passwordInput.value.trim() !== '';

        if (isUsernameFilled && isPasswordFilled) {
            submitBtn.classList.add('active');
            submitIcon.src = 'img/stroke.svg';
        } else {
            submitBtn.classList.remove('active');
            submitIcon.src = 'img/stroke-dark.svg';
        }
    }

    // Функционал кнопки показать/спрятать пароль (оставляем без изменений)
    toggleButton.addEventListener('click', () => {
        const isPassword = passwordInput.getAttribute('type') === 'password';
        passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
        eyeIcon.src = isPassword ? 'img/eye-off.svg' : 'img/eye-open.svg';
    });

    // Модифицированный функционал входа через API
    loginForm.addEventListener('submit', async (e) => { // Добавили async
        e.preventDefault();

        const username = usernameInput.value;
        const password = passwordInput.value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();

                // Сохраняем токен и данные в память браузера
                localStorage.setItem('token', data.token);
                localStorage.setItem('userName', data.user.username);
                localStorage.setItem('userId', data.user.id);

                errorText.classList.remove('_visible');
                passwordInput.classList.remove('_error');

                // Переходим на главную страницу
                window.location.href = '/main.html';
            } else {
                // Если API вернул ошибку (401 и т.д.), показываем визуализацию коллеги
                errorText.classList.add('_visible');
                passwordInput.classList.add('_error');
            }
        } catch (error) {
            console.error('Ошибка при попытке входа:', error);
            // На случай, если бэкенд вообще не запущен
            errorText.textContent = "Сервер недоступен";
            errorText.classList.add('_visible');
        }
    });

    checkInputs();
    passwordInput.addEventListener('input', checkInputs);
    usernameInput.addEventListener('input', checkInputs);
}

/***/ },

/***/ "./src/js/modules/suspects.js"
/*!************************************!*\
  !*** ./src/js/modules/suspects.js ***!
  \************************************/
(__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   initDashboard: () => (/* binding */ initDashboard)
/* harmony export */ });

// Массив теперь пустой, он наполнится данными из API
let suspectsData = [];

// Делаем функцию асинхронной, чтобы дождаться ответа от сервера
const initDashboard = async () => {
    const listContainer = document.querySelector('#suspectsList');
    const slider = document.querySelector('#contentSlider');
    const tabButtons = document.querySelectorAll('.nav-btn');
    const mainContainer = document.querySelector('.main__container');

    const summaryPane = document.querySelector('#tab-summary');
    const operationsPane = document.querySelector('#tab-operations');
    const connectionsPane = document.querySelector('#tab-connections');

    // ─── ЗАГРУЗКА ДАННЫХ С БЭКЕНДА ──────────────────────────────────────────
    const token = localStorage.getItem('token');
    const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname === '/';

    // Если мы НЕ на странице логина и токена нет — только тогда выкидываем
    if (!isLoginPage && !token) {
        window.location.href = '/index.html';
        return;
    }

    // Если мы на странице логина — нам НЕ нужно запускать загрузку данных бэкенда
    if (isLoginPage) {
        return;
    }

    try {
        const response = await fetch('/frauds?limit=50', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 403 || response.status === 401) {
            window.location.href = '/index.html';
            return;
        }

        suspectsData = await response.json();
    } catch (err) {
        console.error("Ошибка при загрузке списка мошенников:", err);
        listContainer.innerHTML = '<p class="white">Ошибка загрузки данных</p>';
        return;
    }

    if (suspectsData.length === 0) {
        listContainer.innerHTML = '<p class="white">Мошенников не обнаружено</p>';
        return;
    }

    // Инициализируем ID первого мошенника из полученных данных
    let currentSuspectId = suspectsData[0].id;

    // ─── Остальная логика коллеги (БЕЗ ИЗМЕНЕНИЙ) ────────────────────────────

    const isMobile = () => window.innerWidth < 876;
    const header = document.querySelector('.header');

    const showDetail = () => {
        mainContainer.classList.add('main__container--detail-view');
        header.classList.add('header--detail-mode');
    };

    const showList = () => {
        mainContainer.classList.remove('main__container--detail-view');
        header.classList.remove('header--detail-mode');
        slider.style.transform = 'translateX(0%)';
        tabButtons.forEach((b, i) => {
            b.classList.toggle('active', i === 0);
        });
    };

    const contentEl = document.querySelector('.content');
    const backBtn = document.createElement('button');
    backBtn.className = 'mobile-back-btn';
    backBtn.textContent = 'Назад';
    backBtn.addEventListener('click', showList);
    contentEl.insertBefore(backBtn, contentEl.firstChild);

    const updateAllPanes = () => {
        const data = suspectsData.find(p => p.id === currentSuspectId);
        if (!data) return;

        const tagsToDisplay = data.tags || data.reasons || [];

        summaryPane.innerHTML = `
            <div class="summary">
                <div class="summary__header">
                    <h1 class="summary__title">${data.name}</h1>
                    <span class="summary__status">${data.status}</span>
                </div>

                <div class="summary__details">
                    <p><span>Телефон</span> <span class="white">${data.phone}</span></p>
                    <p><span>Адрес</span> <span class="white">${data.address}</span></p>
                    <p><span>Банковский счёт</span> <span class="white">${data.bankAccount}</span></p>
                    <p><span>ID на маркетплейсе</span> <span class="white">${data.marketplaceId}</span></p>
                    <p><span>ID мобильного оператора</span> <span class="white">${data.mobileId}</span></p>
                    <p><span>ID в банке</span> <span class="white">${data.bankId}</span></p>
                </div>

                <div class="summary__reasons reasons">
                    <h2 class="reasons__title">Теги</h2>
                    <div class="reasons__list">
                        ${tagsToDisplay.map(tag => `<span class="reason-tag">${tag}</span>`).join('')}
                    </div>
                </div>

                <div class="summary__complaints complaints">
                    <h2 class="complaints__title">Жалобы</h2>
                    <div class="complaints__list">
                        ${data.complaints.map(c => `
                            <div class="complaint-item">
                                <span class="complaint-item__author">${c.author}</span>
                                <span class="complaint-item__text">${c.text}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        operationsPane.innerHTML = `
            <div class="operations">
                <div class="operations__section">
                    <h2 class="operations__title">Переводы</h2>
                    <table class="ops-table">
                        <thead>
                            <tr><th>Дата</th><th>Сумма</th><th>От кого</th><th>Кому</th></tr>
                        </thead>
                        <tbody>
                            ${data.transfers.map(t => `
                                <tr>
                                    <td>${t.date}</td>
                                    <td>${t.sum}</td>
                                    <td>${t.from}</td>
                                    <td>${t.to}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <div class="operations__section">
                    <h2 class="operations__title">Звонки</h2>
                    <table class="ops-table">
                        <thead>
                            <tr><th>Дата</th><th>Длительность</th><th>Кто звонил</th><th>Кому звонили</th></tr>
                        </thead>
                        <tbody>
                            ${data.calls.map(c => `
                                <tr>
                                    <td>${c.date}</td>
                                    <td>${c.duration}</td>
                                    <td>${c.from}</td>
                                    <td>${c.to}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <div class="operations__section">
                    <h2 class="operations__title">Заказы</h2>
                    <table class="ops-table">
                        <thead>
                            <tr><th>Дата</th><th>ID</th><th>ФИО</th><th>Телефон</th><th>Адрес</th></tr>
                        </thead>
                        <tbody>
                            ${data.orders.map(o => `
                                <tr>
                                    <td>${o.date}</td>
                                    <td>${o.id}</td>
                                    <td>${o.fio}</td>
                                    <td>${o.phone}</td>
                                    <td>${o.address}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        const connectionsHtml = (data.connections && data.connections.length > 0)
            ? data.connections.map(person => `
                <div class="suspect-card suspect-card--connection">
                    <div class="suspect-card__info">
                        <p class="suspect-card__name">${person.name}</p>
                        <p class="suspect-card__address">Адрес: <span class="suspect-card__text">${person.address}</span></p>
                        <p class="suspect-card__bank">Банковский аккаунт: <span class="suspect-card__text">${person.bankAccount}</span></p>
                        ${person.phone ? `<p class="suspect-card__phone">Номер телефона: <span class="suspect-card__text">${person.phone}</span></p>` : ''}
                    </div>
                    <div class="suspect-card__threat ${person.threat}">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `).join('')
            : '<p class="white">Связей не обнаружено</p>';

        connectionsPane.innerHTML = `
            <div class="connections">
                <div class="connections__list">
                    ${connectionsHtml}
                </div>
            </div>
        `;
    };

    tabButtons.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const offset = index * (100 / 3);
            slider.style.transform = `translateX(-${offset}%)`;
        });
    });

    const renderList = (dataToRender = suspectsData) => {
        listContainer.innerHTML = dataToRender.map((person) => `
            <div class="suspect-card ${person.id === currentSuspectId ? 'active' : ''}" data-id="${person.id}">
                <div class="suspect-card__threat ${person.threat}">
                    <span></span><span></span><span></span>
                </div>
                <div class="suspect-card__info">
                    <p class="suspect-card__name">${person.name}</p>
                    <p class="suspect-card__address">Адрес: <span class="suspect-card__text">${person.address}</span></p>
                    <p class="suspect-card__bank">Банковский аккаунт: <span class="suspect-card__text">${person.bankAccount}</span></p>
                    <p class="suspect-card__phone">Номер телефона: <span class="suspect-card__text">${person.phone}</span></p>
                </div>
            </div>
        `).join('');

        const cards = listContainer.querySelectorAll('.suspect-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                currentSuspectId = card.dataset.id;
                cards.forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                updateAllPanes();
                if (isMobile()) showDetail();
            });
        });
    };

    const searchInput = document.querySelector('.search-input');
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const filtered = suspectsData.filter(person =>
            person.name.toLowerCase().includes(query) ||
            person.address.toLowerCase().includes(query)
        );
        renderList(filtered);
    });

    renderList();
    updateAllPanes();
};

/***/ }

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		if (!(moduleId in __webpack_modules__)) {
/******/ 			delete __webpack_module_cache__[moduleId];
/******/ 			var e = new Error("Cannot find module '" + moduleId + "'");
/******/ 			e.code = 'MODULE_NOT_FOUND';
/******/ 			throw e;
/******/ 		}
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
// This entry needs to be wrapped in an IIFE because it needs to be isolated against other modules in the chunk.
(() => {
/*!***********************!*\
  !*** ./src/js/app.js ***!
  \***********************/
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var _modules_functions_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./modules/functions.js */ "./src/js/modules/functions.js");
/* harmony import */ var _modules_login_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./modules/login.js */ "./src/js/modules/login.js");
/* harmony import */ var _modules_header_js__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./modules/header.js */ "./src/js/modules/header.js");
/* harmony import */ var _modules_suspects_js__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./modules/suspects.js */ "./src/js/modules/suspects.js");





document.addEventListener('DOMContentLoaded', () => {
    (0,_modules_suspects_js__WEBPACK_IMPORTED_MODULE_3__.initDashboard)();
});
})();

/******/ })()
;