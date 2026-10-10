import { dateFr, mds, moisCourt, nombre, pct } from "./format";

const F = " ";

describe("formats français", () => {
  it("affiche les montants en milliards avec une espace fine", () => {
    expect(mds(36_444_680_000_000)).toBe(`36${F}444,7${F}Mds`);
    expect(mds(5_774_200_000_000, 2)).toBe(`5${F}774,20${F}Mds`);
    expect(mds(null)).toBe("—");
  });
  it("affiche les pourcentages sans décimale", () => {
    expect(pct(0.7096)).toBe(`71${F}%`);
    expect(pct(null)).toBe("—");
  });
  it("groupe les milliers", () => {
    expect(nombre(13426)).toBe(`13${F}426`);
  });
  it("abrège les mois", () => {
    expect(moisCourt("2025-01-01")).toBe("janv.");
    expect(moisCourt("2025-02-01")).toBe("févr.");
    expect(moisCourt("2025-12-01", true)).toBe("déc. 2025");
  });
  it("formate les dates", () => {
    expect(dateFr("2026-09-15")).toBe("15/09/2026");
  });
});
