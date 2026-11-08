"use strict";

const API_URL = "";

const $ = (selector) => document.querySelector(selector);

let currentResult = null;
let activeTab = "form";
let toastTimer = null;
let isGenerating = false;

// -----------------------------
// Уведомления
// -----------------------------

function showToast(message) {
    const toast = $("#toast");

    toast.textContent = message;
    toast.classList.add("visible");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("visible");
    }, 2500);
}

function showError(message) {
    const error = $("#error-message");

    error.textContent = message;
    error.classList.remove("hidden");
}

function hideError() {
    $("#error-message").classList.add("hidden");
}

function formatApiError(detail) {
    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const location = Array.isArray(item.loc)
                    ? item.loc.join(" → ")
                    : "Поле";

                return `${location}: ${item.msg || "Ошибка"}`;
            })
            .join("\n");
    }

    return "Не удалось выполнить запрос.";
}

// -----------------------------
// Проверка API
// -----------------------------

async function checkApi() {
    const statusText = $("#api-status");
    const statusDot = $("#status-dot");

    try {
        const response = await fetch(`${API_URL}/health`, {
            signal: AbortSignal.timeout(5000),
        });

        if (!response.ok) {
            throw new Error("API недоступен");
        }

        statusText.textContent = "API подключён";
        statusDot.classList.add("online");
        statusDot.classList.remove("offline");

    } catch {
        statusText.textContent = "API недоступен";
        statusDot.classList.add("offline");
        statusDot.classList.remove("online");
    }
}

// -----------------------------
// Характеристики
// -----------------------------

function addSpecRow(key = "", value = "") {
    const container = $("#specs-container");

    const row = document.createElement("div");
    row.className = "spec-row";

    const keyInput = document.createElement("input");
    keyInput.type = "text";
    keyInput.className = "spec-key";
    keyInput.placeholder = "Характеристика";
    keyInput.value = key;
    keyInput.setAttribute("aria-label", "Название характеристики");

    const valueInput = document.createElement("input");
    valueInput.type = "text";
    valueInput.className = "spec-value";
    valueInput.placeholder = "Значение";
    valueInput.value = value;
    valueInput.setAttribute("aria-label", "Значение характеристики");

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-spec";
    removeButton.textContent = "×";
    removeButton.setAttribute("aria-label", "Удалить характеристику");

    removeButton.addEventListener("click", () => {
        row.remove();
    });

    row.append(keyInput, valueInput, removeButton);
    container.appendChild(row);
}

function collectSpecs() {
    const specs = {};

    document.querySelectorAll(".spec-row").forEach((row) => {
        const key = row.querySelector(".spec-key").value.trim();
        const value = row.querySelector(".spec-value").value.trim();

        if (!key && !value) {
            return;
        }

        if (!key) {
            throw new Error(
                "У одной из характеристик отсутствует название."
            );
        }

        if (Object.prototype.hasOwnProperty.call(specs, key)) {
            throw new Error(
                `Характеристика «${key}» указана несколько раз.`
            );
        }

        specs[key] = value;
    });

    return specs;
}

// -----------------------------
// Входные данные
// -----------------------------

function collectFormData() {
    const name = $("#product-name").value.trim();
    const manufacturer = $("#manufacturer").value.trim();
    const description = $("#description").value.trim();

    if (!name) {
        throw new Error("Укажите название товара.");
    }

    return {
        name,
        manufacturer: manufacturer || null,
        specs: collectSpecs(),
        description: description || null,
    };
}

function collectJsonData() {
    const raw = $("#json-input").value.trim();

    if (!raw) {
        throw new Error("Вставьте входной JSON.");
    }

    let data;

    try {
        data = JSON.parse(raw);
    } catch (error) {
        throw new Error(`Некорректный JSON: ${error.message}`);
    }

    if (
        data === null ||
        typeof data !== "object" ||
        Array.isArray(data)
    ) {
        throw new Error("Входной JSON должен быть объектом.");
    }

    if (typeof data.name !== "string" || !data.name.trim()) {
        throw new Error("Поле name обязательно.");
    }

    return data;
}

// -----------------------------
// Переключение вкладок
// -----------------------------

document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        if (isGenerating) {
            return;
        }

        activeTab = tab.dataset.tab;

        document.querySelectorAll(".tab").forEach((item) => {
            item.classList.toggle(
                "active",
                item.dataset.tab === activeTab
            );
        });

        $("#form-tab").classList.toggle(
            "active",
            activeTab === "form"
        );

        $("#json-tab").classList.toggle(
            "active",
            activeTab === "json"
        );

        hideError();
    });
});

// -----------------------------
// Форматирование JSON
// -----------------------------

$("#format-json").addEventListener("click", () => {
    try {
        const data = collectJsonData();

        $("#json-input").value = JSON.stringify(
            data,
            null,
            2
        );

        hideError();
        showToast("JSON отформатирован");

    } catch (error) {
        showError(error.message);
    }
});

// -----------------------------
// Генерация
// -----------------------------

function setLoading(loading) {
    isGenerating = loading;

    $("#generate-button").disabled = loading;
    $("#clear-button").disabled = loading;
    $("#add-spec").disabled = loading;
    $("#format-json").disabled = loading;

    document.querySelectorAll(".tab").forEach((tab) => {
        tab.disabled = loading;
    });

    $("#generate-text").textContent = loading
        ? "Генерация..."
        : "✦ Сгенерировать";

    $("#generate-loader").classList.toggle(
        "hidden",
        !loading
    );
}

async function generateProduct(data) {
    const response = await fetch(
        `${API_URL}/api/products/generate`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        }
    );

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error(
            "Сервер вернул ответ, который не является JSON."
        );
    }

    if (!response.ok) {
        throw new Error(formatApiError(result.detail));
    }

    return result;
}

$("#generate-button").addEventListener("click", async () => {
    if (isGenerating) {
        return;
    }

    hideError();

    let data;

    try {
        data = activeTab === "form"
            ? collectFormData()
            : collectJsonData();
    } catch (error) {
        showError(error.message);
        return;
    }

    setLoading(true);

    try {
        const result = await generateProduct(data);

        currentResult = result;
        renderResult(result);

        showToast("Карточка успешно создана");

    } catch (error) {
        showError(
            error instanceof TypeError
                ? "Не удалось подключиться к API. Проверьте запуск FastAPI и настройки CORS."
                : error.message
        );

    } finally {
        setLoading(false);
    }
});

// -----------------------------
// Отображение результата
// -----------------------------

function renderCounter(selector, length, min, max) {
    const element = $(selector);

    element.textContent = min === null
        ? `${length} / ${max}`
        : `${length} / ${min}–${max}`;

    element.classList.toggle(
        "invalid",
        length > max || (min !== null && length < min)
    );
}

function renderSpecifications(specs) {
    const container = $("#specifications-result");
    container.replaceChildren();

    const entries = Object.entries(specs || {});

    if (entries.length === 0) {
        container.textContent = "Характеристики не указаны.";
        return;
    }

    const table = document.createElement("table");
    table.className = "spec-table";

    const tbody = document.createElement("tbody");

    for (const [key, value] of entries) {
        const row = document.createElement("tr");

        const keyCell = document.createElement("td");
        keyCell.textContent = key;

        const valueCell = document.createElement("td");
        valueCell.textContent = value;

        row.append(keyCell, valueCell);
        tbody.appendChild(row);
    }

    table.appendChild(tbody);
    container.appendChild(table);
}

function renderTags(selector, values, className, emptyText) {
    const container = $(selector);
    container.replaceChildren();

    if (!Array.isArray(values) || values.length === 0) {
        container.textContent = emptyText;
        return;
    }

    for (const value of values) {
        const tag = document.createElement("span");

        tag.className = className;
        tag.textContent = value;

        container.appendChild(tag);
    }
}

function renderResult(result) {
    $("#empty-state").classList.add("hidden");
    $("#result-content").classList.remove("hidden");
    $("#copy-all").classList.remove("hidden");

    $("#seo-title").textContent = result.seo_title || "";
    $("#seo-description").textContent = result.seo_description || "";
    $("#commercial-block").textContent = result.commercial_block || "";

    renderCounter(
        "#title-counter",
        (result.seo_title || "").length,
        null,
        70
    );

    renderCounter(
        "#description-counter",
        (result.seo_description || "").length,
        800,
        1200
    );

    renderSpecifications(result.specifications);

    renderTags(
        "#search-queries",
        result.search_queries,
        "tag",
        "Поисковые запросы отсутствуют."
    );

    renderTags(
        "#missing-fields",
        result.missing_fields,
        "missing-tag",
        "Дополнительные сведения не указаны."
    );
}

// -----------------------------
// Копирование
// -----------------------------

async function copyText(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast("Скопировано в буфер обмена");
    } catch {
        showToast("Не удалось скопировать текст");
    }
}

document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", () => {
        const element = document.getElementById(
            button.dataset.copy
        );

        if (element) {
            copyText(element.textContent);
        }
    });
});

$("#copy-all").addEventListener("click", () => {
    if (!currentResult) {
        return;
    }

    copyText(
        JSON.stringify(currentResult, null, 2)
    );
});

// -----------------------------
// Очистка
// -----------------------------

$("#clear-button").addEventListener("click", () => {
    $("#product-name").value = "";
    $("#manufacturer").value = "";
    $("#description").value = "";
    $("#json-input").value = "";

    $("#specs-container").replaceChildren();
    addSpecRow();

    currentResult = null;

    $("#empty-state").classList.remove("hidden");
    $("#result-content").classList.add("hidden");
    $("#copy-all").classList.add("hidden");

    hideError();
    showToast("Данные очищены");
});

// -----------------------------
// Инициализация
// -----------------------------

addSpecRow();
checkApi();