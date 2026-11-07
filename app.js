const form = document.querySelector("#savings-form");
const result = document.querySelector("#result");
const resultAmount = document.querySelector("#result-amount");
const resultDetail = document.querySelector("#result-detail");
const amountSavedOutput = document.querySelector("#amount-saved");
const growthOutput = document.querySelector("#growth-amount");
const breakdownShare = document.querySelector("#breakdown-share");

const fields = [
  { input: document.querySelector("#monthly-saving"), group: "monthly-saving", label: "Monthly savings" },
  { input: document.querySelector("#years"), group: "years", label: "Saving period" },
  { input: document.querySelector("#return-rate"), group: "return-rate", label: "Expected yearly return" },
];

const rupiah = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
});

function validateField(field) {
  const { input, group, label } = field;
  const container = input.closest(".field-group");
  const error = document.querySelector(`#${group}-error`);
  const value = input.value.trim();
  let message = "";

  if (value === "") message = `${label} is required.`;
  else if (!Number.isFinite(Number(value))) message = "Enter a valid number.";
  else if (Number(value) < 0) message = "Please enter zero or a positive number.";

  container.classList.toggle("has-error", Boolean(message));
  error.textContent = message;
  input.setAttribute("aria-invalid", String(Boolean(message)));
  return !message;
}

fields.forEach(({ input }) => {
  input.addEventListener("input", () => {
    if (input.closest(".field-group").classList.contains("has-error")) {
      validateField(fields.find((field) => field.input === input));
    }
  });
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const isValid = fields.map(validateField).every(Boolean);

  if (!isValid) {
    result.hidden = true;
    fields.find(({ input }) => input.getAttribute("aria-invalid") === "true")?.input.focus();
    return;
  }

  const [monthlySaving, years, yearlyReturnPercent] = fields.map(({ input }) => Number(input.value));
  const months = years * 12;
  const monthlyRate = yearlyReturnPercent === 0
    ? 0
    : Math.pow(1 + yearlyReturnPercent / 100, 1 / 12) - 1;
  const futureValue = monthlyRate === 0
    ? monthlySaving * months
    : monthlySaving * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate);
  const amountSaved = monthlySaving * months;
  const growth = futureValue - amountSaved;
  const growthShare = futureValue > 0 ? (growth / futureValue) * 100 : 0;

  resultAmount.textContent = rupiah.format(futureValue);
  resultDetail.textContent = `Based on ${rupiah.format(monthlySaving)} saved monthly for ${years} ${years === 1 ? "year" : "years"}, with an estimated ${yearlyReturnPercent}% yearly return.`;
  amountSavedOutput.textContent = rupiah.format(amountSaved);
  growthOutput.textContent = rupiah.format(growth);
  breakdownShare.textContent = `${growthShare.toFixed(1)}% of your projected balance comes from growth.`;
  result.hidden = false;
});
