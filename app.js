(() => {
  const $ = (id) => document.getElementById(id);
  let selectedTrain = null;
  let selectedJourneyDate = "";

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || "Something went wrong.");
    return payload;
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  function renderTrains(trains) {
    const target = $("trainResults");
    if (!trains.length) {
      target.innerHTML = '<div class="empty">No sample trains found for this route and date. Try another route or date.</div>';
      return;
    }
    target.innerHTML = trains.map(t => `
      <article class="train-card">
        <div><div class="train-name">${esc(t.train_name)}</div><div class="train-no">Train no. ${esc(t.train_number)} · MySQL schedule</div></div>
        <div class="route">
          <div><div class="time">${esc(t.departure_time)}</div><div class="station">${esc(t.source_station)}</div></div>
          <div class="route-line"><span></span>${esc(t.duration)}</div>
          <div><div class="time">${esc(t.arrival_time)}</div><div class="station">${esc(t.destination_station)}</div></div>
        </div>
        <div><div class="fare">₹${Number(t.fare).toLocaleString("en-IN")}<small>per passenger · sample fare</small></div><div class="seats">${Number(t.available_seats)} seats available</div></div>
        <div class="train-actions">
          <button class="primary-btn" data-book="${Number(t.schedule_id)}" ${Number(t.available_seats) < 1 ? "disabled" : ""}>Book ticket</button>
          <button class="secondary-btn" data-details="${Number(t.schedule_id)}">Details</button>
        </div>
      </article>`).join("");
    target.dataset.trains = JSON.stringify(trains);
  }

  async function searchTrains(event) {
    if (event) event.preventDefault();
    const source = $("source").value;
    const destination = $("destination").value;
    const date = $("journeyDate").value;
    if (source === destination) { alert("Please choose two different stations."); return; }
    if (!date) { alert("Please choose a journey date."); return; }
    selectedJourneyDate = date;
    $("resultsTitle").textContent = `${source} to ${destination}`;
    $("resultsSubtitle").textContent = `Sample services for ${new Date(date + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}.`;
    $("trainResults").innerHTML = '<div class="empty">Searching MySQL database…</div>';
    try {
      const qs = new URLSearchParams({ source, destination, date });
      const trains = await requestJson(`/api/trains?${qs}`);
      renderTrains(trains);
    } catch (error) {
      $("trainResults").innerHTML = `<div class="empty">${esc(error.message)}</div>`;
    }
  }

  function buildPassengerFields() {
    const count = Number($("passengerCount").value);
    $("passengerFields").innerHTML = Array.from({ length: count }, (_, i) => `
      <div class="passenger-box">
        <h4>Passenger ${i + 1}</h4>
        <div class="passenger-grid">
          <div class="field"><label>Name</label><input name="passenger_name" maxlength="70" required placeholder="Full name"></div>
          <div class="field"><label>Age</label><input name="passenger_age" type="number" min="1" max="120" required placeholder="Age"></div>
          <div class="field"><label>Gender</label><select name="passenger_gender"><option>Prefer not to say</option><option>Female</option><option>Male</option><option>Other</option></select></div>
        </div>
      </div>`).join("");
  }

  function openBooking(scheduleId) {
    const trains = JSON.parse($("trainResults").dataset.trains || "[]");
    selectedTrain = trains.find(t => Number(t.schedule_id) === Number(scheduleId));
    if (!selectedTrain) return;
    if (document.body.dataset.loggedIn !== "true") {
      window.location.href = "/login";
      return;
    }
    $("selectedTrainText").textContent = `${selectedTrain.train_name} · ${selectedTrain.source_station} → ${selectedTrain.destination_station} · ${selectedJourneyDate} · ₹${Number(selectedTrain.fare).toLocaleString("en-IN")} per passenger`;
    $("passengerCount").value = "1";
    buildPassengerFields();
    $("bookingModal").classList.add("open");
  }

  async function loadBookings() {
    const target = $("bookingList");
    if (!target) return;
    try {
      const bookings = await requestJson("/api/bookings");
      if (!bookings.length) {
        target.innerHTML = '<div class="empty">No bookings yet. Search for a train and book your first demo ticket.</div>';
        return;
      }
      target.innerHTML = bookings.map(b => `
        <div class="booking-row">
          <div><b>${esc(b.train_name)}</b><div class="booking-meta">${esc(b.source_station)} → ${esc(b.destination_station)} · ${esc(b.journey_date)}<br>PNR: <b>${esc(b.pnr_number)}</b> · ${Number(b.number_of_passengers)} passenger(s) · ₹${Number(b.total_fare).toLocaleString("en-IN")}</div></div>
          <div><span class="status ${b.booking_status === "CANCELLED" ? "cancelled" : ""}">${esc(b.booking_status)}</span>
          ${b.booking_status === "CONFIRMED" ? `<div style="margin-top:10px"><button class="secondary-btn" data-cancel="${Number(b.booking_id)}">Cancel ticket</button></div>` : ""}</div>
        </div>`).join("");
    } catch (error) {
      target.innerHTML = `<div class="empty">${esc(error.message)}. Please log in again if your session expired.</div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("searchForm")?.addEventListener("submit", searchTrains);
    $("trainResults")?.addEventListener("click", (event) => {
      const book = event.target.closest("[data-book]");
      const details = event.target.closest("[data-details]");
      if (book) openBooking(book.dataset.book);
      if (details) {
        const trains = JSON.parse($("trainResults").dataset.trains || "[]");
        const t = trains.find(item => Number(item.schedule_id) === Number(details.dataset.details));
        if (t) alert(`${t.train_name}\nTrain number: ${t.train_number}\nRoute: ${t.source_station} to ${t.destination_station}\nDeparture: ${t.departure_time}\nArrival: ${t.arrival_time}\nDuration: ${t.duration}\nSample fare: ₹${t.fare}\nAvailable seats: ${t.available_seats}`);
      }
    });
    $("passengerCount")?.addEventListener("change", buildPassengerFields);
    $("closeModal")?.addEventListener("click", () => $("bookingModal").classList.remove("open"));
    $("bookingModal")?.addEventListener("click", e => { if (e.target === $("bookingModal")) $("bookingModal").classList.remove("open"); });
    document.querySelector("[data-close-confirm]")?.addEventListener("click", () => $("confirmationModal").classList.remove("open"));

    $("bookingForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!selectedTrain) return;
      const names = [...document.querySelectorAll('[name="passenger_name"]')];
      const ages = [...document.querySelectorAll('[name="passenger_age"]')];
      const genders = [...document.querySelectorAll('[name="passenger_gender"]')];
      const passengers = names.map((el, i) => ({ name: el.value.trim(), age: Number(ages[i].value), gender: genders[i].value }));
      const submit = $("bookingForm").querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        const result = await requestJson("/api/bookings", {
          method: "POST",
          body: JSON.stringify({ schedule_id: selectedTrain.schedule_id, passenger_count: passengers.length, passengers })
        });
        $("bookingModal").classList.remove("open");
        $("confirmationBody").innerHTML = `<div class="confirmation"><div style="font-size:42px">✅</div><h3>Booking confirmed!</h3><p class="small-muted">Your record has been saved in MySQL.</p><div class="pnr">${esc(result.pnr)}</div><p><b>${esc(result.train_name)}</b><br>${esc(result.source_station)} → ${esc(result.destination_station)}<br>${esc(result.journey_date)} · ${result.passenger_count} passenger(s)</p><p>Total sample fare: <b>₹${Number(result.total_fare).toLocaleString("en-IN")}</b></p><button class="primary-btn" id="showBookings">View my bookings</button></div>`;
        $("confirmationModal").classList.add("open");
        $("showBookings").addEventListener("click", () => {
          $("confirmationModal").classList.remove("open");
          $("my-bookings")?.scrollIntoView({ behavior: "smooth" });
          loadBookings();
        });
        await searchTrains();
        await loadBookings();
      } catch (error) {
        alert(error.message);
      } finally {
        submit.disabled = false;
      }
    });

    $("bookingList")?.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-cancel]");
      if (!button || !confirm("Cancel this booking? The demo seats will be restored.")) return;
      button.disabled = true;
      try {
        const result = await requestJson(`/api/bookings/${button.dataset.cancel}/cancel`, { method: "POST", body: "{}" });
        alert(result.message);
        await loadBookings();
        await searchTrains();
      } catch (error) {
        alert(error.message);
        button.disabled = false;
      }
    });

    if ($("trainResults")) {
      // Initial route search shows real records fetched from MySQL.
      searchTrains();
      loadBookings();
    }
  });
})();
