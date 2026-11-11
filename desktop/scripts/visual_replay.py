"""Exercise the real native presentation; imported by native_replay.py only."""

import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

PAGES = [
    "État",
    "Fournisseurs",
    "Profils & règles",
    "Consommation",
    "Inspecteur",
    "Réglages",
]


def verify_presentation(driver, evidence, button, select, check, screen):
    layouts = []
    button("Masquer la notification")
    check(
        "export notice can be dismissed",
        not driver.find_elements(By.CSS_SELECTOR, ".alert.success"),
    )
    for theme in ("dark", "light"):
        button("Réglages")
        select("Thème de l’interface", theme)
        check(
            f"manual {theme} theme applied through UI",
            driver.execute_script("return document.documentElement.dataset.theme")
            == theme,
        )
        expected = "rgb(9, 13, 15)" if theme == "dark" else "rgb(240, 243, 234)"
        check(
            f"{theme} approved background token",
            driver.execute_script(
                "return getComputedStyle(document.documentElement).backgroundColor"
            )
            == expected,
        )
        for width, height in ((1180, 820), (800, 640)):
            driver.set_window_size(width, height)
            for index, page in enumerate(PAGES):
                button(page)
                screen(f"visual-{theme}-{width}-{index + 1}")
                layout = driver.execute_script("""return {
                  width: innerWidth, height: innerHeight, scroll: document.documentElement.scrollWidth,
                  selected: document.querySelector('.nav[aria-current="page"]')?.textContent,
                  images: [...document.images].every(i => i.complete && i.naturalWidth > 0),
                  bounds: [...document.querySelectorAll('main, header, .card, .filters, .save-bar')].map(e => ({
                    class: e.className, left: e.getBoundingClientRect().left,
                    right: e.getBoundingClientRect().right, client: e.clientWidth, scroll: e.scrollWidth
                  }))};""")
                layout.update(theme=theme, page=page)
                driver.execute_script(
                    "window.scrollTo(0, document.documentElement.scrollHeight)"
                )
                time.sleep(0.2)
                driver.save_screenshot(
                    str(evidence / f"visual-{theme}-{width}-{index + 1}-bottom.png")
                )
                check(
                    f"{theme}/{width}/{page}: page bottom reachable",
                    driver.execute_script(
                        "return scrollY + innerHeight >= document.documentElement.scrollHeight - 1"
                    ),
                )
                layouts.append(layout)
                check(
                    f"{theme}/{width}/{page}: selected nav and logo",
                    page in layout["selected"] and layout["images"],
                )
                check(
                    f"{theme}/{width}/{page}: no viewport overflow",
                    layout["scroll"] <= layout["width"]
                    and all(
                        b["left"] >= 0
                        and b["right"] <= layout["width"] + 1
                        and b["scroll"] <= b["client"] + 1
                        for b in layout["bounds"]
                    ),
                )
        driver.set_window_size(1180, 820)
        button("État")
        check(
            f"{theme}: topology represents observed receipts",
            bool(
                driver.find_elements(
                    By.CSS_SELECTOR, '.topology-route[data-selected="true"]'
                )
            ),
        )
        screen(f"visual-{theme}-overview-observed")
        button("Inspecteur")
        opener = driver.find_elements(By.CSS_SELECTOR, ".receipt")[0]
        opener.click()
        check(
            f"{theme}: structured receipt is readable",
            "Modèle confirmé" in driver.find_element(By.CSS_SELECTOR, ".dialog").text,
        )
        driver.find_element(By.CSS_SELECTOR, ".dialog summary").click()
        screen(f"visual-{theme}-receipt-expanded")
        driver.switch_to.active_element.send_keys(Keys.TAB)
        check(
            f"{theme}: dialog keyboard focus is trapped",
            driver.execute_script("return !!document.activeElement.closest('.dialog')"),
        )
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        check(
            f"{theme}: Escape restores opener focus",
            driver.switch_to.active_element == opener,
        )
        # A real operation failure, supplied by the synthetic API, is captured by caller.
    button("Réglages")
    select("Thème de l’interface", "system")
    check(
        "system theme selection restored",
        driver.execute_script("return document.documentElement.dataset.theme")
        == "system",
    )
    button("État")
    driver.find_element(By.CSS_SELECTOR, '.nav[aria-current="page"]').send_keys(
        Keys.TAB
    )
    check(
        "keyboard focus has a visible outline",
        driver.execute_script(
            "return getComputedStyle(document.activeElement).outlineStyle !== 'none'"
        ),
    )
    screen("visual-keyboard-focus")
    (evidence / "visual-layouts.json").write_text(
        json.dumps(layouts, indent=2, ensure_ascii=False)
    )
