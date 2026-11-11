# Contrôles OMR

Les boutons, champs, listes et cases à cocher utilisent les tokens clair/sombre de `styles.css`, sans relief système superposé. Le sélecteur partagé `Select` utilise Radix déjà installé : son trigger et sa liste ouverte suivent les mêmes tokens OMR. Le clavier, la recherche par caractères, les options désactivées, Escape et le retour du focus sont gérés par la primitive accessible.

## Contrat du sélecteur

```tsx
<Select
  value={transport}
  onValueChange={setTransport}
  options={[
    { value: "http", label: "HTTP" },
    { value: "pi-ai", label: "pi-ai" },
  ]}
/>
```

`value` est une chaîne contrôlée, y compris `""` (par exemple « Aucune référence »). `options` est un tableau readonly de `{ value: string; label: string; disabled?: boolean }`. Les valeurs sont uniques. `id`, `name`, `disabled`, `className`, `aria-label`, `aria-labelledby` et `aria-describedby` sont facultatifs. `name` conserve la valeur applicative dans les données du formulaire, sans exposer l’encodage interne Radix. Le composant ne soumet pas le formulaire à l’ouverture.

Un `<Field>` ou un `<label>` enveloppant nomme le trigger bouton. Les listes sont portalisées hors des panneaux et dialogues scrollables, mais restent dans le thème actif porté par `html[data-theme]`. Leur hauteur suit l’espace disponible ; les longs libellés restent lisibles sans déborder.

Les appelants restent dans la lane `t_702b81af` : importer `Select` depuis `./components/ui`, remplacer `onChange={(e) => …e.target.value}` par `onValueChange={(value) => …value}` et convertir les anciens enfants `option` en tableau `options`. Conserver les conversions numériques et `value || null`. Cette carte ne modifie pas `App.tsx`. La composition doit vérifier qu’aucun ancien `<select>` visible ne reste dans les formulaires.

Les champs HTML conservent labels, Tab, saisie numérique, validation, readonly et disabled. Les switches utilisent Radix. Le focus visible reste distinct du survol. En couleurs forcées, les champs natifs et les couleurs système préservent la lisibilité ; le menu Radix reste accessible et adopte Canvas/Highlight.

## Régression de rendu

Depuis `desktop/` :

```sh
npm test -- src/components/controls.test.tsx
uv run --python 3.13.5 --with playwright==1.56.0 python scripts/test_controls_render.py --css src/styles.css --evidence test-results/controls-linux-source
npm run build
uv run --python 3.13.5 --with playwright==1.56.0 python scripts/test_controls_render.py --evidence test-results/controls-linux-production
```

Le replay monte les vrais composants React partagés dans un contexte Brave Linux isolé, avec la feuille de production ou celle spécifiée. Il vérifie la liste effectivement ouverte (fond, surlignage, option sélectionnée), clavier, labels, valeur vide, disabled, formulaires et absence de débordement en clair/sombre aux largeurs 800 et 1180. Les captures sont des fixtures synthétiques, pas une preuve de l’application native, du menu macOS ou d’un fournisseur connecté. La barre macOS reste à qualifier dans la lane release.
