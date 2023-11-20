# Code group editor

This folder contains the program for creating groups of ICD-10 and OPCS-4 codes.

## Developer Dependencies (Linux)

```bash
# To install system dependencies (Ubuntu 22.04 LTS)
sudo apt install libgtk-3-dev libsoup-gnome2.4-dev libjavascriptcoregtk-4.0-dev libwebkit2gtk-4.0-dev
```

## Rust Dependencies

Install rustup according to the [instructions](https://www.rust-lang.org/tools/install) for Linux. Install the Tauri client according to the [documentation](https://tauri.app/v1/guides/getting-started/setup/next-js) using:

```bash
cargo install tauri-cli
```

## Node Dependencies

```bash
# To install node dependencies
npm install
 ```

The command to develop is `cargo tauri dev`. The command to build the release version is `cargo tauri build`. The resulting binary will be located in `src-tauri\target\release\codes-editor.exe`

## Notes

On 20/11/2023, when setting up the CI for the release build (Github), the following error occurred in the runner:

```bash
Failed to compile.

./pages/_app.tsx:5:11
Type error: 'Component' cannot be used as a JSX component.
  Its element type 'Component<any, any, any> | ReactElement<any, any> | null' is not a valid JSX element.
    Type 'Component<any, any, any>' is not assignable to type 'Element | ElementClass | null'.
      Type 'Component<any, any, any>' is not assignable to type 'ElementClass'.
        The types returned by 'render()' are incompatible between these types.
          Type 'React.ReactNode' is not assignable to type 'import("/home/runner/work/hbr_models/hbr_models/codes_editor/node_modules/@types/react-dom/node_modules/@types/react/ts5.0/index").ReactNode'.
            Type 'ReactElement<any, string | JSXElementConstructor<any>>' is not assignable to type 'ReactNode'.
              Property 'children' is missing in type 'ReactElement<any, string | JSXElementConstructor<any>>' but required in type 'ReactPortal'.

  3 | 
  4 | export default function App({ Component, pageProps }: AppProps) {
> 5 |   return <Component {...pageProps} />
    |           ^
  6 | }
  7 | 
       Error beforeBuildCommand `npm run build && npm run export` failed with exit code 1
Error: Command failed with exit code 1: tauri build
```

This error was fixed by following the instructions [here](https://stackoverflow.com/questions/71831601/ts2786-component-cannot-be-used-as-a-jsx-component), by adding the `resolutions` block to the `package.json` file.