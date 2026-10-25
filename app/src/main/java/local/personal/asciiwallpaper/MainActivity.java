package local.personal.asciiwallpaper;

import android.app.*;
import android.content.Intent;
import android.database.Cursor;
import android.provider.OpenableColumns;
import android.graphics.*;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.*;
import android.widget.*;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public class MainActivity extends Activity {
    private static final int PICK = 10, EXPORT = 11, LOGS = 12;
    private static final String[] MODES = {"auto", "natural", "shadow", "shadow2", "detail",
        "structure", "retinex", "edge", "twotone", "braille", "halfblock", "original"};
    private static final String[] FITS = {"auto", "contain", "cover", "stretch"};
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final List<View> controls = new ArrayList<>();
    private TextView status;
    private TextView imageInfo;
    private Button imageInfoToggle;
    private boolean imageInfoExpanded;
    private ImageView preview;
    private EditText size, fontSize, background;
    private Spinner mode, fit, sizePolicy;
    private ArrayAdapter<String> sizeAdapter;
    private final List<String> sizeLabels = new ArrayList<>();
    private int sourceWidth, sourceHeight, deviceWidth, deviceHeight, sizePolicyIndex;
    private String customSize;
    private CheckBox autoBackground, dither;
    private String sourcePath, resultPath;
    private Bitmap previewBitmap;
    private boolean busy;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(12), dp(16), dp(12));
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                view.setPadding(dp(16) + bars.left, dp(12) + bars.top,
                    dp(16) + bars.right, dp(12) + bars.bottom);
                return insets;
            });
        }
        ScrollView scroll = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL); scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, -1)); setContentView(root);
        label(content, "ASCII 壁纸生成器").setTextSize(24);
        preview = new ImageView(this); preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
        content.addView(preview, new LinearLayout.LayoutParams(-1, dp(260)));
        button(content, "选择图片", () -> {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*");
            intent.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(intent, PICK);
        });
        imageInfoToggle = new Button(this);
        imageInfoToggle.setText("▶ 图片信息");
        imageInfoToggle.setOnClickListener(v -> {
            imageInfoExpanded = !imageInfoExpanded;
            updateImageInfoPanel();
        });
        content.addView(imageInfoToggle);
        imageInfo = label(content, "选择图片后自动读取图片信息。");
        imageInfo.setTextIsSelectable(true);
        updateImageInfoPanel();
        mode = spinner(content, "渲染算法", new String[]{"自动推荐", "自然增强", "暗部细节",
            "暗部细节 v2", "细节增强（CLAHE）", "结构线条", "Retinex", "边缘保持",
            "双色字符格", "盲文点阵", "半块字符", "原始算法"});
        fit = spinner(content, "图片适配", new String[]{"自动", "完整显示", "铺满裁切", "拉伸（旧版）"});
        int width = getResources().getDisplayMetrics().widthPixels;
        int height = getResources().getDisplayMetrics().heightPixels;
        WallpaperManager manager = WallpaperManager.getInstance(this);
        if (manager.getDesiredMinimumWidth() > 0 && manager.getDesiredMinimumHeight() > 0) {
            width = manager.getDesiredMinimumWidth(); height = manager.getDesiredMinimumHeight();
        }
        deviceWidth = width; deviceHeight = height;
        customSize = width + "x" + height;
        sizePolicy = spinner(content, "输出尺寸", new String[]{
            "原图尺寸（选图后自动读取）", "设备壁纸尺寸（" + width + "×" + height + "）", "自定义尺寸"});
        sizeLabels.addAll(Arrays.asList("原图尺寸（选图后自动读取）",
            "设备壁纸尺寸（" + width + "×" + height + "）", "自定义尺寸"));
        sizeAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, sizeLabels);
        sizeAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        sizePolicy.setAdapter(sizeAdapter);
        size = input(content, "宽×高", "", false);
        size.setHint("选择图片后自动填入");
        fontSize = input(content, "字体大小（6–64）", "18", true);
        background = input(content, "手动背景色（如 #101820）", "black", false);
        autoBackground = check(content, "自动背景", true);
        dither = check(content, "误差扩散", false);
        button(content, "生成预览", this::generate);
        button(content, "设为壁纸", this::chooseWallpaperTarget);
        button(content, "另存 PNG", () -> export(EXPORT, "image/png", "ascii-wallpaper.png"));
        button(content, "导出诊断日志", () -> export(LOGS, "text/plain", "ascii-wallpaper-log.txt"));
        status = label(content, "请选择图片。生成结果保存在应用内部，可通过“另存 PNG”导出。");
        if (state != null) {
            sourcePath = state.getString("source"); resultPath = state.getString("result");
            sourceWidth = state.getInt("sourceWidth"); sourceHeight = state.getInt("sourceHeight");
            imageInfo.setText(state.getString("imageInfo", "选择图片后自动读取图片信息。"));
            imageInfoExpanded = state.getBoolean("imageInfoExpanded");
            updateImageInfoPanel();
            customSize = state.getString("customSize", customSize);
            sizePolicyIndex = state.getInt("sizePolicy");
            fontSize.setText(state.getString("font", "18"));
            background.setText(state.getString("background", "black"));
            mode.setSelection(state.getInt("mode")); fit.setSelection(state.getInt("fit"));
            autoBackground.setChecked(state.getBoolean("autoBackground", true));
            dither.setChecked(state.getBoolean("dither"));
            if (resultPath != null && new File(resultPath).isFile()) showPreview();
        }
        refreshSourceSizeLabel();
        sizePolicy.setSelection(sizePolicyIndex);
        updateOutputSize();
        sizePolicy.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (sizePolicyIndex == 2) customSize = size.getText().toString();
                sizePolicyIndex = position;
                updateOutputSize();
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });
    }
    private void updateImageInfoPanel() {
        imageInfoToggle.setText(imageInfoExpanded ? "▼ 图片信息" : "▶ 图片信息");
        imageInfoToggle.setContentDescription(imageInfoExpanded ? "收起图片信息" : "展开图片信息");
        imageInfo.setVisibility(imageInfoExpanded ? View.VISIBLE : View.GONE);
    }
    private void refreshSourceSizeLabel() {
        sizeLabels.set(0, sourceWidth > 0 && sourceHeight > 0
            ? "原图尺寸（" + sourceWidth + "×" + sourceHeight + "）" : "原图尺寸（选图后自动读取）");
        sizeAdapter.notifyDataSetChanged();
    }
    private void updateOutputSize() {
        if (sizePolicyIndex == 0) {
            size.setText(sourceWidth > 0 && sourceHeight > 0 ? sourceWidth + "x" + sourceHeight : "");
        } else if (sizePolicyIndex == 1) {
            size.setText(deviceWidth + "x" + deviceHeight);
        } else {
            size.setText(customSize);
        }
        size.setEnabled(!busy && sizePolicyIndex == 2);
    }
    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
    private TextView label(LinearLayout parent, String text) {
        TextView v = new TextView(this); v.setText(text); v.setTextSize(16);
        v.setPadding(0, dp(8), 0, dp(4)); parent.addView(v); return v;
    }
    private void button(LinearLayout parent, String text, Runnable action) {
        Button v = new Button(this); v.setText(text);
        v.setOnClickListener(unused -> { try { action.run(); } catch (Exception e) { fail(e); } });
        parent.addView(v); controls.add(v);
    }
    private EditText input(LinearLayout parent, String name, String value, boolean numeric) {
        label(parent, name); EditText v = new EditText(this); v.setSingleLine(true);
        if (numeric) v.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        v.setText(value); parent.addView(v); controls.add(v); return v;
    }
    private Spinner spinner(LinearLayout parent, String name, String[] labels) {
        label(parent, name); Spinner v = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, labels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        v.setAdapter(adapter); parent.addView(v); controls.add(v); return v;
    }
    private CheckBox check(LinearLayout parent, String name, boolean checked) {
        CheckBox v = new CheckBox(this); v.setText(name); v.setChecked(checked);
        parent.addView(v); controls.add(v); return v;
    }
    private void busy(boolean value, String message) {
        busy = value; controls.forEach(v -> v.setEnabled(!value)); status.setText(message);
        size.setEnabled(!value && sizePolicyIndex == 2);
    }
    private void completed(Runnable action) {
        runOnUiThread(() -> { if (!isDestroyed() && !isFinishing()) action.run(); });
    }
    private void fail(Exception error) {
        writeLog(error); completed(() -> busy(false, "操作失败：" + error.getMessage()));
    }
    @Override protected void onActivityResult(int request, int code, Intent data) {
        super.onActivityResult(request, code, data);
        if (code != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData(); busy(true, "正在读写文件…");
        worker.execute(() -> {
            try {
                if (request == PICK) {
                    File imported = new File(getFilesDir(), "selected-image.tmp");
                    File partial = new File(getFilesDir(), "selected-image.partial");
                    try (InputStream in = getContentResolver().openInputStream(uri);
                         OutputStream out = new FileOutputStream(partial)) { copy(in, out); }
                    if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
                    List<com.chaquo.python.PyObject> dimensions = Python.getInstance()
                        .getModule("android_renderer").callAttr("source_size", partial.getAbsolutePath()).asList();
                    int imageWidth = dimensions.get(0).toInt(), imageHeight = dimensions.get(1).toInt();
                    String metadata;
                    try {
                        metadata = Python.getInstance().getModule("android_renderer").callAttr("image_info",
                            partial.getAbsolutePath(), displayName(uri)).toString();
                    } catch (Exception metadataError) {
                        writeLog(metadataError);
                        metadata = "图片信息暂时无法完整读取。\n显示尺寸：" + imageWidth + "×" + imageHeight;
                    }
                    final String infoText = metadata;
                    Files.move(partial.toPath(), imported.toPath(), StandardCopyOption.REPLACE_EXISTING);
                    completed(() -> {
                        sourcePath = imported.getAbsolutePath(); sourceWidth = imageWidth; sourceHeight = imageHeight;
                        imageInfo.setText(infoText);
                        refreshSourceSizeLabel(); updateOutputSize();
                        busy(false, "图片已导入：" + imageWidth + "×" + imageHeight + "。");
                    });
                } else {
                    try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                        if (out == null) throw new IOException("无法打开导出位置");
                        if (request == EXPORT) {
                            try (InputStream in = new FileInputStream(resultPath)) { copy(in, out); }
                        } else {
                            for (String name : new String[]{"app.log", "app.log.1", "renderer.log", "renderer.log.1", "renderer.log.2"}) {
                                File file = new File(logDir(), name);
                                if (file.isFile()) {
                                    out.write(("\n--- " + name + " ---\n").getBytes(StandardCharsets.UTF_8));
                                    try (InputStream in = new FileInputStream(file)) { copy(in, out); }
                                }
                            }
                        }
                    }
                    completed(() -> busy(false, "已导出。"));
                }
            } catch (Exception e) { fail(e); }
        });
    }
    private String displayName(Uri uri) {
        try (Cursor cursor = getContentResolver().query(uri,
                new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0 && !cursor.isNull(index)) return cursor.getString(index);
            }
        } catch (Exception ignored) { /* A provider need not expose a display name. */ }
        return "未知文件名";
    }
    private static void copy(InputStream in, OutputStream out) throws IOException {
        if (in == null) throw new IOException("无法读取所选文件");
        byte[] buffer = new byte[65536]; int count;
        while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
    }
    private void generate() {
        if (busy) return;
        if (sourcePath == null) { status.setText("请先选择图片。"); return; }
        String[] parts = size.getText().toString().trim().toLowerCase(Locale.ROOT).split("x");
        if (parts.length != 2) throw new IllegalArgumentException("尺寸格式应为 1080x1920");
        int width = Integer.parseInt(parts[0]), height = Integer.parseInt(parts[1]);
        int font = Integer.parseInt(fontSize.getText().toString());
        if (width < 1 || height < 1 || (long) width * height > 16000000L)
            throw new IllegalArgumentException("输出尺寸须为正数且不超过 1600 万像素；原图过大时请选择自定义尺寸");
        if (font < 6 || font > 64) throw new IllegalArgumentException("字体大小必须在 6–64 之间");
        String algorithm = MODES[mode.getSelectedItemPosition()], fitting = FITS[fit.getSelectedItemPosition()];
        String bg = autoBackground.isChecked() ? "auto" : background.getText().toString().trim();
        boolean useDither = dither.isChecked(); String source = sourcePath;
        busy(true, "正在生成…");
        worker.execute(() -> {
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
                File output = new File(getFilesDir(), "wallpaper.png");
                File pending = new File(getFilesDir(), "wallpaper-pending.png");
                String selected = Python.getInstance().getModule("android_renderer").callAttr("render",
                    source, pending.getAbsolutePath(), renderFont(), width, height, font,
                    algorithm, fitting, bg, useDither, logDir().getAbsolutePath()).toString();
                Files.move(pending.toPath(), output.toPath(), StandardCopyOption.REPLACE_EXISTING);
                completed(() -> { resultPath = output.getAbsolutePath(); showPreview();
                    busy(false, "生成完成：" + selected + "，" + width + "×" + height); });
            } catch (Exception e) { fail(e); }
        });
    }
    private String renderFont() throws IOException {
        for (String path : new String[]{"/system/fonts/RobotoMono-Regular.ttf",
                "/system/fonts/NotoSansMono-Regular.ttf", "/system/fonts/DroidSansMono.ttf",
                "/system/fonts/Roboto-Regular.ttf"}) {
            if (new File(path).isFile()) return path;
        }
        throw new IOException("未找到可用渲染字体");
    }
    private void showPreview() {
        BitmapFactory.Options options = new BitmapFactory.Options(); options.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(resultPath, options); options.inSampleSize = 1;
        while (Math.max(options.outWidth, options.outHeight) / options.inSampleSize > 1200) options.inSampleSize *= 2;
        options.inJustDecodeBounds = false;
        Bitmap next = BitmapFactory.decodeFile(resultPath, options); preview.setImageBitmap(next);
        if (previewBitmap != null) previewBitmap.recycle(); previewBitmap = next;
    }
    private void chooseWallpaperTarget() {
        if (resultPath == null) { status.setText("请先生成壁纸。"); return; }
        new AlertDialog.Builder(this).setTitle("设置壁纸")
            .setItems(new String[]{"主屏幕", "锁屏", "主屏幕和锁屏"}, (dialog, index) -> {
                int flags = index == 0 ? WallpaperManager.FLAG_SYSTEM : index == 1
                    ? WallpaperManager.FLAG_LOCK : WallpaperManager.FLAG_SYSTEM | WallpaperManager.FLAG_LOCK;
                String path = resultPath; busy(true, "正在设置壁纸…");
                worker.execute(() -> {
                    try (InputStream in = new FileInputStream(path)) {
                        WallpaperManager.getInstance(this).setStream(in, null, true, flags);
                        completed(() -> busy(false, "壁纸已设置。"));
                    } catch (Exception e) { fail(e); }
                });
            }).show();
    }
    private void export(int request, String mime, String name) {
        if (request == EXPORT && resultPath == null) { status.setText("请先生成壁纸。"); return; }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).setType(mime);
        intent.addCategory(Intent.CATEGORY_OPENABLE); intent.putExtra(Intent.EXTRA_TITLE, name);
        startActivityForResult(intent, request);
    }
    private File logDir() { File dir = new File(getFilesDir(), "logs"); dir.mkdirs(); return dir; }
    private synchronized void writeLog(Throwable error) {
        Log.e("AsciiWallpaper", "Operation failed", error); File log = new File(logDir(), "app.log");
        try {
            if (log.length() > 1024 * 1024) Files.move(log.toPath(), new File(logDir(), "app.log.1").toPath(),
                StandardCopyOption.REPLACE_EXISTING);
            try (PrintWriter writer = new PrintWriter(new OutputStreamWriter(
                    new FileOutputStream(log, true), StandardCharsets.UTF_8))) {
                writer.println(new Date()); error.printStackTrace(writer);
            }
        } catch (IOException e) { Log.e("AsciiWallpaper", "Cannot write log", e); }
    }
    @Override public void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state); state.putString("source", sourcePath); state.putString("result", resultPath);
        state.putInt("sourceWidth", sourceWidth); state.putInt("sourceHeight", sourceHeight);
        state.putString("imageInfo", imageInfo.getText().toString());
        state.putBoolean("imageInfoExpanded", imageInfoExpanded);
        state.putInt("sizePolicy", sizePolicyIndex);
        state.putString("customSize", sizePolicyIndex == 2 ? size.getText().toString() : customSize);
        state.putString("font", fontSize.getText().toString());
        state.putString("background", background.getText().toString());
        state.putInt("mode", mode.getSelectedItemPosition()); state.putInt("fit", fit.getSelectedItemPosition());
        state.putBoolean("autoBackground", autoBackground.isChecked()); state.putBoolean("dither", dither.isChecked());
    }
    @Override protected void onDestroy() {
        worker.shutdown(); preview.setImageDrawable(null);
        if (previewBitmap != null) previewBitmap.recycle(); super.onDestroy();
    }
}
