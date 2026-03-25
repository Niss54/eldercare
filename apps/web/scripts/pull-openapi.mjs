import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const DEFAULT_SOURCE = "http://localhost:8000/openapi.json";
const source = process.env.OPENAPI_SOURCE_URL ?? DEFAULT_SOURCE;
const targetDir = join(process.cwd(), "openapi");
const targetFile = join(targetDir, "openapi.json");

const response = await fetch(source);
if (!response.ok) {
  throw new Error(`Failed to fetch OpenAPI schema from ${source}: ${response.status} ${response.statusText}`);
}

const schema = await response.text();
await mkdir(targetDir, { recursive: true });
await writeFile(targetFile, schema, "utf8");

console.log(`Wrote OpenAPI schema to ${targetFile}`);
