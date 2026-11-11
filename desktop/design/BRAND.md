# Logo fourni — provenance et dérivés desktop

## Source inchangée

`originals/upload_3smffdyj.png` : PNG RGB, 1254 × 1254, fourni par Zacaria. SHA-256 : `e07bb3cfb80edc8e5be8ec2f74959330784a934bf9f850ae08450c86ee8bfd05`. Le PNG original est conservé, sans substitution par un dessin vectoriel. La référence UI et sa consigne sont dans le même dossier ; elles ne sont pas embarquées dans les paquets ni chargées par l’application.

## Génération bornée

Depuis `desktop/` :

```sh
uv run --python 3.13.5 --with pillow==12.0.0 python scripts/build_brand.py
uv run --python 3.13.5 --with pillow==12.0.0 python scripts/test_brand.py
```

Le générateur vérifie le hash source. Il supprime seulement les pixels extérieurs presque noirs reliés au bord (seuil maximum RGB 16), recadre le carré `(80, 80, 1174, 1174)`, puis réduit sans étirement. Les proportions, flux entrant et trois sorties menthe/violet/orange sont conservés. Les coins RGBA restent transparents ; les détails sombres internes ne sont pas découpés.

| Dérivé | Usage |
| --- | --- |
| `public/brand/app-128.png` | Marque dans la navigation et favicon local |
| `src-tauri/icons/icon.png` | PNG 512, icône native Linux et ressource Tauri |
| `src-tauri/icons/icon.ico` | Windows : 16/24/32/48/64/128/256 |
| `src-tauri/icons/icon.icns` | macOS : conteneur desktop, jusqu’à 1024 |
| `src-tauri/icons/tray.png` | Tray Windows/Linux, signe de routage citron sur plaque sombre contrastée, 32 × 32 |
| `src-tauri/icons/tray-template.png` | Template macOS noir/alpha 44 × 32, recoloré par l’OS |

Le tray est une **extraction des pixels du signe de routage**, non un retracé du Y seul : crop `(180,220,1120,1010)`, sélection des pixels lumineux et colorés (`max(RGB) > 100`, `max(RGB) - min(RGB) > 40`), conservation des composantes connexes d’au moins 5 000 pixels pour retirer les reflets isolés du cadre. L’entrée, la jonction et les trois destinations sont conservées. Un épaississement optique de 9 pixels au format source puis un échantillonnage Lanczos dans 40 × 28 pixels assurent un contour compact. Le canevas macOS 44 × 32 respecte le rapport du signe ; sa mise à l’échelle effective doit être vérifiée dans la barre de menus native. Le tray couleur réduit ce même alpha dans 28 × 28 sur sa plaque sombre. La profondeur 3D, les couleurs distinctes et les reflets ne sont pas reproduits dans le template ; les trois destinations restent séparées. L’ICNS, l’ICO et le logo web complet restent inchangés.

Aucun format mobile, Store ou service distant n’est généré. L’ancien `icon.svg`, non référencé, est supprimé pour ne pas conserver deux identités concurrentes. Les six dérivés sont contrôlés par `build_brand.py --check` ; leur manifeste Tauri conserve la liste explicite PNG/ICO/ICNS. `main.rs` sélectionne déjà le template seulement sur macOS et reste inchangé dans cette correction, ainsi que les menus et le cycle de vie.

## Vérification par couche

Source et dérivés : hashes, tailles, canaux alpha, lecture des conteneurs et reproduction exacte. Rendu de cette correction : `test-results/brand-linux-raster/linux-pillow-tray-contact-sheet.png`, comparant le Y antérieur et le signe complet sur clair/sombre à des hauteurs de 16/18/24/32 px. À 16–18 px, le centre reste dense et les trois destinations ne sont pas toutes distinctes ; à 32 px elles se séparent. L’agrandissement 6× est un diagnostic de pixels, pas une taille de ressource supplémentaire. Le contrôle automatique exige trois bandes de destinations séparées dans l’alpha 44 × 32. Les vérifications historiques webview/paquet Linux ne sont pas rejouées ici.

Le build Linux et ses captures ne qualifient pas un Dock macOS, une taskbar Windows ou un tray Linux réellement affiché par un environnement de bureau (Xvfb n’en fournit pas). La release `t_a3a76415` vérifie ces surfaces ainsi que les métadonnées ICNS et signatures sur leurs OS respectifs.
