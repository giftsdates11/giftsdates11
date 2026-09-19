import React, { useState } from "react";
import { Crown, Plus, X, Sparkles, Lock, MapPin, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { api, fileUrl } from "../lib/api";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";
import { detectLocation } from "../lib/geolocate";
import { normalizeCountry } from "../lib/countries";
import { matchCuratedCity } from "../lib/cities";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { VIP_CATEGORIES, VIP_PLACES, PRICE_KEYS, svcLabel, catTitle, placeLabel, priceLabel } from "../lib/vipCatalog";
import { GENDERS } from "./ProfileDetailsForm";
import CountrySelect from "./CountrySelect";
import CitySelect from "./CitySelect";
import MultiSelect from "./MultiSelect";

// Appearance option lists for the standalone anonymous VIP profile.
const EYE_COLORS = ["Brown", "Hazel", "Amber", "Green", "Blue", "Grey", "Black", "Heterochromia"];
const HAIR_COLORS = ["Black", "Dark brown", "Brown", "Light brown", "Blonde", "Platinum blonde", "Red", "Auburn", "Ginger", "Grey", "White", "Dyed / colourful"];
const INTIMATE_HAIRCUTS = ["Fully shaved", "Trimmed", "Landing strip", "Bikini line", "Natural / full", "Triangle"];
const BREAST_SIZES = ["AA", "A", "B", "C", "D", "DD", "E", "F", "G", "H+", "Natural", "Enhanced"];
const DICK_SIZES = ["< 12 cm", "12–14 cm", "15–17 cm", "18–20 cm", "21–23 cm", "24+ cm"];
const DICK_GIRTHS = ["Slim", "Average", "Thick", "Very thick", "< 10 cm", "10–12 cm", "13–15 cm", "16+ cm"];

const NONE_VAL = "__none";
const CUSTOM_VAL = "__custom";

// A dropdown with all preset options plus a "Custom (type)…" entry that reveals a free-text input.
function AttrSelect({ label, value, onChange, options, lang, testid }) {
  const isPreset = value && options.includes(value);
  const isCustom = !!value && !isPreset;
  const selectVal = isPreset ? value : (isCustom ? CUSTOM_VAL : NONE_VAL);
  return (
    <div>
      <label className="text-xs text-slate-400">{label}</label>
      <Select
        value={selectVal}
        onValueChange={(v) => {
          if (v === NONE_VAL) onChange("");
          else if (v === CUSTOM_VAL) onChange(" ");
          else onChange(v);
        }}
      >
        <SelectTrigger data-testid={testid} className="bg-white/5 border-white/10 mt-1"><SelectValue /></SelectTrigger>
        <SelectContent className="bg-[#161320] border-white/10 text-white max-h-72">
          <SelectItem value={NONE_VAL}>{t("not_specified_short", lang)}</SelectItem>
          {options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          <SelectItem value={CUSTOM_VAL}>{t("vip_attr_custom", lang)}</SelectItem>
        </SelectContent>
      </Select>
      {isCustom && (
        <Input
          data-testid={`${testid}-custom`}
          value={value.trim() === "" ? "" : value}
          maxLength={60}
          onChange={(e) => onChange(e.target.value || " ")}
          placeholder={t("vip_attr_custom_ph", lang)}
          className="bg-white/5 border-white/10 mt-2"
        />
      )}
    </div>
  );
}

export default function VipEditor() {
  const { user, refreshUser, lang } = useApp();
  const nav = useNavigate();
  const isVip = user?.is_vip || (user?.vip_until && new Date(user.vip_until) > new Date());
  const v = user?.vip || {};
  const [services, setServices] = useState(v.services || []);
  const [servicesNote, setServicesNote] = useState(v.services_note || "");
  const [prices, setPrices] = useState(v.prices || { hour: "", h2: "", h3: "" });
  const [places, setPlaces] = useState(v.places || []);
  const [wants, setWants] = useState(v.client_wants || "");
  const [slots, setSlots] = useState(v.availability || []);
  const [ns, setNs] = useState({ date: "", from: "18:00", to: "23:00" });
  const [photos, setPhotos] = useState(v.photos || []);
  const [privatePhotos, setPrivatePhotos] = useState(v.private_photos || []);
  const [nickname, setNickname] = useState(v.nickname || "");
  const [postMode, setPostMode] = useState(v.post_mode === "separate" ? "separate" : "together");
  const [sepAge, setSepAge] = useState(v.age || "");
  const [sepCity, setSepCity] = useState(v.city || "");
  const [sepCountry, setSepCountry] = useState(v.country || "");
  const [sepGenders, setSepGenders] = useState(v.genders || (v.gender ? [v.gender] : []));
  const [sepBio, setSepBio] = useState(v.bio || "");
  const [sepHeight, setSepHeight] = useState(v.height || "");
  const [sepWeight, setSepWeight] = useState(v.weight || "");
  const [sepEye, setSepEye] = useState(v.eye_color || "");
  const [sepHair, setSepHair] = useState(v.hair_color || "");
  const [sepHaircut, setSepHaircut] = useState(v.intimate_haircut || "");
  const [sepBreast, setSepBreast] = useState(v.breast_size || "");
  const [sepDick, setSepDick] = useState(v.dick_size || "");
  const [sepDickGirth, setSepDickGirth] = useState(v.dick_girth || "");
  const [showOnMain, setShowOnMain] = useState(v.show_on_main !== false);
  const [published, setPublished] = useState(v.published !== false);
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);
  const photoRef = React.useRef(null);
  const privateRef = React.useRef(null);
  const goBuyVip = () => { toast.info(t("vip_upsell", lang)); nav("/wallet?vip=1"); };
  const detectMyLocation = async () => {
    setLocating(true);
    try {
      const { city, country } = await detectLocation(lang);
      const normCountry = normalizeCountry(country);
      const nearestCity = matchCuratedCity(city, normCountry);
      if (normCountry) setSepCountry(normCountry);
      if (nearestCity) setSepCity(nearestCity);
      toast.success(t("location_detected", lang) + (nearestCity ? ` · ${nearestCity}${normCountry ? ", " + normCountry : ""}` : ""));
    } catch {
      toast.error(t("location_failed", lang));
    } finally {
      setLocating(false);
    }
  };
  const addPhoto = async (e, isPrivate = false) => {
    const f = e.target.files?.[0]; if (!f) return;
    const list = isPrivate ? privatePhotos : photos;
    if (list.length >= 12) { toast.error(t("vip_max_photos", lang)); return; }
    const fd = new FormData(); fd.append("photo", f);
    try {
      const { data } = await api.post(`/vip/photo?private=${isPrivate}`, fd);
      setPhotos(data.photos); setPrivatePhotos(data.private_photos);
    }
    catch (er) { toast.error(er.response?.data?.detail === "MAX_PHOTOS" ? t("vip_max_photos", lang) : "Ошибка"); }
    finally { const ref = isPrivate ? privateRef : photoRef; if (ref.current) ref.current.value = ""; }
  };
  const delPhoto = async (p, isPrivate = false) => {
    try { const { data } = await api.delete(`/vip/photo?path=${encodeURIComponent(p)}&private=${isPrivate}`); setPhotos(data.photos); setPrivatePhotos(data.private_photos); } catch { toast.error("Ошибка"); }
  };
  const makeCover = async (p) => {
    const reordered = [p, ...photos.filter((x) => x !== p)];
    setPhotos(reordered);
    try { await api.post("/vip/photos/reorder", { photos: reordered }); toast.success(t("vip_cover_updated", lang)); } catch { toast.error("Ошибка"); }
  };

  const toggle = (arr, set, val) => set(arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  // Gender-aware appearance: show breast fields for feminine identities, dick fields for masculine ones.
  const FEMININE = ["female", "cis_woman"];
  const MASCULINE = ["male", "cis_man"];
  const onlyFeminine = sepGenders.length > 0 && sepGenders.every((g) => FEMININE.includes(g));
  const onlyMasculine = sepGenders.length > 0 && sepGenders.every((g) => MASCULINE.includes(g));
  const showBreast = !onlyMasculine; // hide only when purely masculine
  const showDick = !onlyFeminine;    // hide only when purely feminine
  const addSlot = () => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(ns.date) || ns.from >= ns.to) { toast.error("Укажите дату и корректное время"); return; }
    setSlots([...slots, { ...ns }].sort((a, b) => (a.date + a.from).localeCompare(b.date + b.from)));
  };
  const onTogglePublish = (val) => {
    if (!isVip) { goBuyVip(); return; }
    setPublished(val);
  };
  const save = async () => {
    setBusy(true);
    try {
      await api.put("/vip/profile", {
        services, services_note: servicesNote, places, client_wants: wants,
        price_hour: Number(prices.hour) || 0, price_2h: Number(prices.h2) || 0, price_3h: Number(prices.h3) || 0,
        availability: slots, published: isVip ? published : false,
        nickname, post_mode: postMode,
        age: Number(sepAge) || null, city: sepCity, country: sepCountry, gender: sepGenders[0] || "", genders: sepGenders, bio: sepBio,
        height: Number(sepHeight) || null, weight: Number(sepWeight) || null,
        eye_color: (sepEye || "").trim(), hair_color: (sepHair || "").trim(), intimate_haircut: (sepHaircut || "").trim(),
        breast_size: showBreast ? (sepBreast || "").trim() : "", dick_size: showDick ? (sepDick || "").trim() : "", dick_girth: showDick ? (sepDickGirth || "").trim() : "",
        show_on_main: showOnMain,
      });
      await refreshUser();
      toast.success(t("vip_saved_toast", lang));
    } catch (e) { toast.error(e.response?.data?.detail || "Ошибка"); } finally { setBusy(false); }
  };

  return (
    <div className="glass rounded-2xl p-6 mb-6 border border-rose-500/30 space-y-5" data-testid="vip-editor">
      <div className={`rounded-2xl p-4 border ${isVip ? "border-amber-500/30 bg-amber-500/5" : "border-amber-500/40 bg-amber-500/10"}`} data-testid="vip-publish-box">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Crown className="text-amber-300 shrink-0" size={22} />
            <div>
              <div className="text-sm font-semibold text-amber-100">{t("vip_publish_toggle", lang)}</div>
              <div className="text-xs text-slate-400">{isVip ? (published ? t("vip_live", lang) : t("vip_hidden", lang)) : t("vip_preview_note", lang)}</div>
            </div>
          </div>
          <Switch data-testid="vip-publish-switch" checked={isVip && published} onCheckedChange={onTogglePublish} />
        </div>
        {!isVip && (
          <Button data-testid="vip-buy-publish-cta" onClick={goBuyVip} className="rose-btn text-white border-0 mt-3 w-full sm:w-auto"><Sparkles size={16} className="me-1" /> {t("vip_buy_publish", lang)}</Button>
        )}
      </div>

      <h2 className="font-serif-luxe text-2xl gold-text flex items-center gap-2"><Crown size={22} className="text-amber-300" /> {t("vip_editor_title", lang)}</h2>
      <p className="text-xs text-slate-400">{t("vip_editor_note", lang)}</p>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-semibold text-amber-200">{t("vip_nickname", lang)}</label>
          <Input data-testid="vip-nickname-input" value={nickname} maxLength={40} onChange={(e) => setNickname(e.target.value)} placeholder={t("vip_nickname_ph", lang)} className="bg-white/5 border-white/10 mt-1" />
          <p className="text-[11px] text-slate-500 mt-1 flex items-start gap-1"><Lock size={11} className="mt-0.5 shrink-0 text-amber-300" /> {t("vip_nickname_note", lang)}</p>
        </div>
        <div>
          <label className="text-sm font-semibold text-amber-200">{t("vip_post_mode", lang)}</label>
          <div className="mt-1 grid grid-cols-2 gap-2" data-testid="vip-post-mode">
            {[{ v: "together", l: "vip_post_together" }, { v: "separate", l: "vip_post_separate" }].map((o) => (
              <button key={o.v} type="button" data-testid={`vip-post-mode-${o.v}`} onClick={() => setPostMode(o.v)}
                className={`text-xs px-3 py-2 rounded-lg border transition-colors ${postMode === o.v ? "bg-amber-500/20 border-amber-500/50 text-amber-200" : "bg-white/5 border-white/10 text-slate-300 hover:bg-white/10"}`}>{t(o.l, lang)}</button>
            ))}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">{t("vip_post_mode_note", lang)}</p>
        </div>
      </div>

      {postMode === "separate" && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-4" data-testid="vip-separate-block">
          <div className="flex items-start gap-2 text-[11px] text-amber-200/90">
            <Lock size={13} className="mt-0.5 shrink-0 text-amber-300" />
            <span>{t("vip_separate_intro", lang)}</span>
          </div>
          <div className="grid sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-slate-400">{t("age", lang)}</label>
              <Input data-testid="vip-sep-age" type="number" min="18" max="99" value={sepAge} onChange={(e) => setSepAge(e.target.value)} className="bg-white/5 border-white/10 mt-1 font-mono-num" />
            </div>
            <div>
              <label className="text-xs text-slate-400">{t("country", lang)}</label>
              <CountrySelect testid="vip-sep-country" value={sepCountry} onChange={(c) => { setSepCountry(c); setSepCity(""); }} lang={lang} />
            </div>
            <div>
              <label className="text-xs text-slate-400">{t("city", lang)}</label>
              <CitySelect testid="vip-sep-city" value={sepCity} country={sepCountry} onChange={setSepCity} lang={lang} />
            </div>
          </div>
          <button
            type="button"
            data-testid="vip-sep-detect-location"
            onClick={detectMyLocation}
            disabled={locating}
            className="w-full inline-flex items-center justify-center gap-2 h-10 rounded-lg border border-sky-500/40 bg-sky-500/10 text-sky-200 text-sm hover:bg-sky-500/20 transition-colors disabled:opacity-60"
          >
            {locating ? <Loader2 size={15} className="animate-spin" /> : <MapPin size={15} />}
            {locating ? t("detecting_location", lang) : t("detect_location", lang)}
          </button>
          <div>
            <label className="text-xs text-slate-400">{t("gender", lang)}</label>
            <div className="mt-1" data-testid="vip-sep-gender">
              <MultiSelect
                testid="vip-sep-gender-select"
                accent="amber"
                value={sepGenders}
                onChange={setSepGenders}
                options={GENDERS.map((g) => ({ value: g, label: t(g, lang) }))}
                placeholder={t("gender", lang)}
                searchPlaceholder={t("search", lang)}
                emptyText={t("no_results", lang)}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">{t("vip_separate_bio", lang)}</label>
            <Textarea data-testid="vip-sep-bio" rows={2} maxLength={1000} value={sepBio} onChange={(e) => setSepBio(e.target.value)} placeholder={t("vip_separate_bio_ph", lang)} className="bg-white/5 border-white/10 mt-1" />
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3" data-testid="vip-sep-appearance">
            <div className="text-sm font-semibold text-amber-200">{t("vip_appearance", lang)}</div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400">{t("height", lang)}</label>
                <Input data-testid="vip-sep-height" type="number" min="100" max="250" value={sepHeight} onChange={(e) => setSepHeight(e.target.value)} className="bg-white/5 border-white/10 mt-1 font-mono-num" />
              </div>
              <div>
                <label className="text-xs text-slate-400">{t("weight", lang)}</label>
                <Input data-testid="vip-sep-weight" type="number" min="30" max="400" value={sepWeight} onChange={(e) => setSepWeight(e.target.value)} className="bg-white/5 border-white/10 mt-1 font-mono-num" />
              </div>
              <AttrSelect testid="vip-sep-eye" label={t("vip_eye_color", lang)} value={sepEye} onChange={setSepEye} options={EYE_COLORS} lang={lang} />
              <AttrSelect testid="vip-sep-hair" label={t("vip_hair_color", lang)} value={sepHair} onChange={setSepHair} options={HAIR_COLORS} lang={lang} />
              <AttrSelect testid="vip-sep-haircut" label={t("vip_intimate_haircut", lang)} value={sepHaircut} onChange={setSepHaircut} options={INTIMATE_HAIRCUTS} lang={lang} />
              {showBreast && <AttrSelect testid="vip-sep-breast" label={t("vip_breast_size", lang)} value={sepBreast} onChange={setSepBreast} options={BREAST_SIZES} lang={lang} />}
              {showDick && <AttrSelect testid="vip-sep-dick" label={t("vip_dick_size", lang)} value={sepDick} onChange={setSepDick} options={DICK_SIZES} lang={lang} />}
              {showDick && <AttrSelect testid="vip-sep-dick-girth" label={t("vip_dick_girth", lang)} value={sepDickGirth} onChange={setSepDickGirth} options={DICK_GIRTHS} lang={lang} />}
            </div>
          </div>
          <div className="flex items-center justify-between gap-3 rounded-xl bg-white/5 border border-white/10 px-3 py-2.5">
            <div>
              <div className="text-sm font-semibold text-amber-100">{t("vip_show_on_main", lang)}</div>
              <div className="text-[11px] text-slate-400">{t("vip_show_on_main_note", lang)}</div>
            </div>
            <Switch data-testid="vip-show-on-main-switch" checked={showOnMain} onCheckedChange={setShowOnMain} />
          </div>
        </div>
      )}


      <div data-testid="vip-photos">
        <div className="text-sm font-semibold text-amber-200 mb-2">{t("vip_public_photos", lang)}</div>
        <div className="flex flex-wrap gap-2">
          {photos.map((p, i) => (
            <div key={p} className="relative w-20 h-20 rounded-lg overflow-hidden gold-hairline group">
              <img src={fileUrl(p)} alt="" className="w-full h-full object-cover" />
              {i === 0 && <span className="absolute bottom-0 left-0 right-0 bg-amber-500/80 text-[9px] text-black text-center">{t("vip_cover", lang)}</span>}
              {i !== 0 && <button data-testid="vip-photo-cover" onClick={() => makeCover(p)} className="absolute bottom-0 left-0 right-0 bg-black/70 text-[9px] text-amber-200 text-center opacity-0 group-hover:opacity-100">{t("vip_make_cover", lang)}</button>}
              <button data-testid="vip-photo-del" onClick={() => delPhoto(p, false)} className="absolute top-0 right-0 bg-black/70 text-rose-300 p-0.5"><X size={12} /></button>
            </div>
          ))}
          {photos.length < 12 && (
            <>
              <input ref={photoRef} data-testid="vip-photo-input" type="file" accept="image/*" onChange={(e) => addPhoto(e, false)} className="hidden" id="vip-photo" />
              <label htmlFor="vip-photo" className="w-20 h-20 rounded-lg border-2 border-dashed border-amber-400/50 flex items-center justify-center text-amber-300 cursor-pointer hover:bg-white/5"><Plus size={20} /></label>
            </>
          )}
        </div>
      </div>

      <div data-testid="vip-private-photos">
        <div className="text-sm font-semibold text-rose-200 mb-1 flex items-center gap-1.5"><Lock size={14} className="text-rose-300" /> {t("vip_private_photos", lang)}</div>
        <p className="text-[11px] text-slate-500 mb-2">{t("vip_private_photos_note", lang)}</p>
        <div className="flex flex-wrap gap-2">
          {privatePhotos.map((p) => (
            <div key={p} className="relative w-20 h-20 rounded-lg overflow-hidden border border-rose-500/40 group">
              <img src={fileUrl(p)} alt="" className="w-full h-full object-cover" />
              <button data-testid="vip-private-photo-del" onClick={() => delPhoto(p, true)} className="absolute top-0 right-0 bg-black/70 text-rose-300 p-0.5"><X size={12} /></button>
            </div>
          ))}
          {privatePhotos.length < 12 && (
            <>
              <input ref={privateRef} data-testid="vip-private-photo-input" type="file" accept="image/*" onChange={(e) => addPhoto(e, true)} className="hidden" id="vip-private-photo" />
              <label htmlFor="vip-private-photo" className="w-20 h-20 rounded-lg border-2 border-dashed border-rose-400/50 flex items-center justify-center text-rose-300 cursor-pointer hover:bg-white/5"><Plus size={20} /></label>
            </>
          )}
        </div>
      </div>

      <div data-testid="vip-services">
        <div className="text-sm font-semibold text-amber-200 mb-2">{t("vip_services", lang)}</div>
        <MultiSelect
          testid="vip-services-select"
          accent="rose"
          value={services}
          onChange={setServices}
          groups={VIP_CATEGORIES.map((cat) => ({
            label: catTitle(cat.key, lang),
            options: cat.items.map((it) => ({ value: it, label: svcLabel(it, lang) })),
          }))}
          placeholder={t("vip_services_ph", lang)}
          searchPlaceholder={t("search", lang)}
          emptyText={t("no_results", lang)}
        />
        <Textarea
          data-testid="vip-services-note"
          rows={2}
          maxLength={500}
          value={servicesNote}
          onChange={(e) => setServicesNote(e.target.value)}
          placeholder={t("vip_services_note_ph", lang)}
          className="bg-white/5 border-white/10 mt-2"
        />
        <p className="text-[11px] text-slate-500 mt-1">{t("vip_services_note_hint", lang)}</p>
      </div>

      <div>
        <div className="text-sm font-semibold text-amber-200 mb-2">{t("vip_prices", lang)}</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {PRICE_KEYS.map((p) => (
            <div key={p.k}>
              <label className="text-xs text-slate-400">{priceLabel(p.k, lang)}</label>
              <Input data-testid={`vip-price-${p.k}`} type="number" min="0" step="50" value={prices[p.k] ?? ""} onChange={(e) => setPrices({ ...prices, [p.k]: e.target.value })} className="bg-white/5 border-white/10 mt-1 font-mono-num" />
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-sm font-semibold text-amber-200 mb-2">{t("vip_place", lang)}</div>
        <MultiSelect
          testid="vip-places-select"
          accent="amber"
          value={places}
          onChange={setPlaces}
          options={VIP_PLACES.map((p) => ({ value: p.v, label: placeLabel(p.v, lang) }))}
          placeholder={t("vip_place_ph", lang)}
          searchPlaceholder={t("search", lang)}
          emptyText={t("no_results", lang)}
        />
      </div>

      <div>
        <div className="text-sm font-semibold text-amber-200 mb-2">{t("vip_calendar", lang)}</div>
        <div className="flex flex-wrap items-end gap-2 mb-2">
          <Input data-testid="vip-slot-date" type="date" value={ns.date} onChange={(e) => setNs({ ...ns, date: e.target.value })} className="bg-white/5 border-white/10 w-40" />
          <Input data-testid="vip-slot-from" type="time" value={ns.from} onChange={(e) => setNs({ ...ns, from: e.target.value })} className="bg-white/5 border-white/10 w-28" />
          <span className="text-slate-500">–</span>
          <Input data-testid="vip-slot-to" type="time" value={ns.to} onChange={(e) => setNs({ ...ns, to: e.target.value })} className="bg-white/5 border-white/10 w-28" />
          <Button data-testid="vip-slot-add" onClick={addSlot} variant="outline" className="bg-white/5 border-white/15"><Plus size={15} /></Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {slots.map((s, i) => (
            <span key={i} data-testid={`vip-slot-${i}`} className="text-xs bg-white/5 gold-hairline rounded-lg px-2.5 py-1 flex items-center gap-2 text-slate-200">
              {s.date} · {s.from}–{s.to}
              <button onClick={() => setSlots(slots.filter((_, j) => j !== i))} className="text-rose-300"><X size={12} /></button>
            </span>
          ))}
          {slots.length === 0 && <span className="text-xs text-slate-500">{t("vip_no_slots", lang)}</span>}
        </div>
      </div>

      <div>
        <div className="text-sm font-semibold text-amber-200 mb-2">{t("vip_wants", lang)}</div>
        <Textarea data-testid="vip-wants" rows={3} maxLength={1000} value={wants} onChange={(e) => setWants(e.target.value)} placeholder={t("vip_wants_ph", lang)} className="bg-white/5 border-white/10" />
      </div>

      <Button data-testid="vip-save" onClick={save} disabled={busy} className="rose-btn text-white border-0 h-11 w-full">{busy ? "…" : t("vip_save_btn", lang)}</Button>
    </div>
  );
}
