import sharp from "sharp";
import fs from "fs";
import path from "path";

const uiDir = path.resolve("../UI");
const outDir = path.resolve("public/backgrounds");

fs.mkdirSync(outDir, { recursive: true });

// Prefer a photo (jpg/jpeg) over the UI mockup reference (a screenshot,
// typically a .png) that may also live in this folder.
const files = fs.readdirSync(uiDir);
const imageFile =
  files.find((file) => /\.(jpe?g)$/i.test(file)) ??
  files.find((file) => /\.(png|webp)$/i.test(file));

if (!imageFile) {
  throw new Error("Fant ikke bakgrunnsbilde i /UI");
}

const inputPath = path.join(uiDir, imageFile);

async function createBackground(width, height, outputName) {
  await sharp(inputPath)
    .resize(width, height, {
      fit: "cover",
      position: "center",
    })
    .webp({ quality: 80 })
    .toFile(path.join(outDir, outputName));
}

await createBackground(1920, 1080, "app-bg.webp");
await createBackground(1280, 720, "app-bg-1280.webp");

console.log("Bakgrunnsbilder generert fra", inputPath);
