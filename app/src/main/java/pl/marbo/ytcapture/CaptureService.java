package pl.marbo.ytcapture;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.provider.MediaStore;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.TextView;
import android.widget.Toast;

import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class CaptureService extends Service {
    public static final String ACTION_STOP = "pl.marbo.ytcapture.STOP";
    public static final String EXTRA_RESULT_CODE = "resultCode";
    public static final String EXTRA_RESULT_DATA = "resultData";

    private static final String CHANNEL_ID = "marbo_capture";
    private static final int NOTIFICATION_ID = 4401;

    private final Handler main = new Handler();
    private HandlerThread imageThread;
    private Handler imageHandler;

    private MediaProjection mediaProjection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private WindowManager windowManager;
    private TextView bubble;
    private WindowManager.LayoutParams bubbleParams;

    private volatile boolean captureRequested = false;
    private int captureWidth;
    private int captureHeight;
    private int densityDpi;

    @Override
    public void onCreate() {
        super.onCreate();
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        imageThread = new HandlerThread("MARBO-Capture");
        imageThread.start();
        imageHandler = new Handler(imageThread.getLooper());
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }

        if (mediaProjection != null) {
            return START_NOT_STICKY;
        }

        Notification notification = buildNotification();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }

        if (intent == null) {
            stopSelf();
            return START_NOT_STICKY;
        }

        int resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0);
        Intent resultData;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            resultData = intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent.class);
        } else {
            resultData = intent.getParcelableExtra(EXTRA_RESULT_DATA);
        }

        if (resultCode == 0 || resultData == null) {
            Toast.makeText(this, "Brak zgody na przechwytywanie ekranu.", Toast.LENGTH_LONG).show();
            stopSelf();
            return START_NOT_STICKY;
        }

        try {
            MediaProjectionManager manager =
                    (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
            mediaProjection = manager.getMediaProjection(resultCode, resultData);
            mediaProjection.registerCallback(new MediaProjection.Callback() {
                @Override
                public void onStop() {
                    main.post(() -> {
                        releaseResources(false);
                        stopSelf();
                    });
                }
            }, imageHandler);

            readDisplayMetrics();
            imageReader = newImageReader(captureWidth, captureHeight);
            virtualDisplay = mediaProjection.createVirtualDisplay(
                    "MARBO-YT-Capture",
                    captureWidth,
                    captureHeight,
                    densityDpi,
                    DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                    imageReader.getSurface(),
                    null,
                    imageHandler);
            showBubble();
        } catch (Exception e) {
            Toast.makeText(this, "Nie udało się uruchomić przechwytywania: " + e.getMessage(), Toast.LENGTH_LONG).show();
            stopSelf();
        }

        return START_NOT_STICKY;
    }

    private ImageReader newImageReader(int width, int height) {
        ImageReader reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 3);
        reader.setOnImageAvailableListener(r -> {
            Image image = null;
            try {
                image = r.acquireLatestImage();
                if (image == null) return;

                if (captureRequested) {
                    captureRequested = false;
                    boolean saved = saveImage(image);
                    main.post(() -> {
                        if (bubble != null) bubble.setVisibility(View.VISIBLE);
                        Toast.makeText(this,
                                saved ? "Zapisano w Pictures/MARBO YT Capture" : "Nie udało się zapisać obrazu.",
                                Toast.LENGTH_SHORT).show();
                    });
                }
            } catch (Exception e) {
                captureRequested = false;
                main.post(() -> {
                    if (bubble != null) bubble.setVisibility(View.VISIBLE);
                    Toast.makeText(this, "Błąd zrzutu: " + e.getMessage(), Toast.LENGTH_LONG).show();
                });
            } finally {
                if (image != null) image.close();
            }
        }, imageHandler);
        return reader;
    }

    private void beginCapture() {
        if (bubble == null || virtualDisplay == null || captureRequested) return;

        bubble.setVisibility(View.INVISIBLE);
        main.postDelayed(() -> {
            boolean resized = ensureCurrentDisplaySize();
            main.postDelayed(() -> captureRequested = true, resized ? 450 : 180);
            main.postDelayed(() -> {
                if (captureRequested) {
                    captureRequested = false;
                    if (bubble != null) bubble.setVisibility(View.VISIBLE);
                    Toast.makeText(this, "Nie otrzymano obrazu z ekranu.", Toast.LENGTH_SHORT).show();
                }
            }, 2600);
        }, 180);
    }

    private boolean ensureCurrentDisplaySize() {
        DisplayMetrics dm = new DisplayMetrics();
        windowManager.getDefaultDisplay().getRealMetrics(dm);
        int newWidth = dm.widthPixels;
        int newHeight = dm.heightPixels;
        int newDensity = dm.densityDpi;

        if (newWidth == captureWidth && newHeight == captureHeight && newDensity == densityDpi) {
            return false;
        }

        try {
            ImageReader replacement = newImageReader(newWidth, newHeight);
            virtualDisplay.resize(newWidth, newHeight, newDensity);
            virtualDisplay.setSurface(replacement.getSurface());
            ImageReader old = imageReader;
            imageReader = replacement;
            captureWidth = newWidth;
            captureHeight = newHeight;
            densityDpi = newDensity;
            if (old != null) old.close();
            repositionBubble();
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean saveImage(Image image) {
        Bitmap padded = null;
        Bitmap cropped = null;
        Uri uri = null;
        try {
            Image.Plane plane = image.getPlanes()[0];
            ByteBuffer buffer = plane.getBuffer();
            int pixelStride = plane.getPixelStride();
            int rowStride = plane.getRowStride();
            int rowPadding = rowStride - pixelStride * image.getWidth();
            int paddedWidth = image.getWidth() + Math.max(0, rowPadding / pixelStride);

            padded = Bitmap.createBitmap(paddedWidth, image.getHeight(), Bitmap.Config.ARGB_8888);
            padded.copyPixelsFromBuffer(buffer);
            cropped = Bitmap.createBitmap(padded, 0, 0, image.getWidth(), image.getHeight());

            String name = "MARBO_YT_" + new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)
                    .format(new Date()) + ".png";

            ContentValues values = new ContentValues();
            values.put(MediaStore.Images.Media.DISPLAY_NAME, name);
            values.put(MediaStore.Images.Media.MIME_TYPE, "image/png");
            values.put(MediaStore.Images.Media.RELATIVE_PATH,
                    Environment.DIRECTORY_PICTURES + "/MARBO YT Capture");
            values.put(MediaStore.Images.Media.IS_PENDING, 1);

            uri = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
            if (uri == null) return false;

            try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                if (out == null || !cropped.compress(Bitmap.CompressFormat.PNG, 100, out)) {
                    getContentResolver().delete(uri, null, null);
                    return false;
                }
            }

            values.clear();
            values.put(MediaStore.Images.Media.IS_PENDING, 0);
            getContentResolver().update(uri, values, null, null);
            return true;
        } catch (Exception e) {
            if (uri != null) {
                try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) { }
            }
            return false;
        } finally {
            if (cropped != null && cropped != padded) cropped.recycle();
            if (padded != null) padded.recycle();
        }
    }

    private void showBubble() {
        if (bubble != null) return;

        bubble = new TextView(this);
        bubble.setText("📷");
        bubble.setTextSize(30);
        bubble.setGravity(Gravity.CENTER);
        bubble.setTextColor(Color.WHITE);
        bubble.setElevation(dp(10));

        GradientDrawable bg = new GradientDrawable();
        bg.setShape(GradientDrawable.OVAL);
        bg.setColor(Color.rgb(211, 47, 47));
        bg.setStroke(dp(2), Color.WHITE);
        bubble.setBackground(bg);

        bubbleParams = new WindowManager.LayoutParams(
                dp(68),
                dp(68),
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                        WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.TRANSLUCENT);
        bubbleParams.gravity = Gravity.TOP | Gravity.START;
        repositionBubble();

        final float[] downX = new float[1];
        final float[] downY = new float[1];
        final int[] startX = new int[1];
        final int[] startY = new int[1];

        bubble.setOnTouchListener((v, event) -> {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downX[0] = event.getRawX();
                    downY[0] = event.getRawY();
                    startX[0] = bubbleParams.x;
                    startY[0] = bubbleParams.y;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    bubbleParams.x = startX[0] + Math.round(event.getRawX() - downX[0]);
                    bubbleParams.y = startY[0] + Math.round(event.getRawY() - downY[0]);
                    try { windowManager.updateViewLayout(bubble, bubbleParams); } catch (Exception ignored) { }
                    return true;
                case MotionEvent.ACTION_UP:
                    float dx = event.getRawX() - downX[0];
                    float dy = event.getRawY() - downY[0];
                    if (Math.hypot(dx, dy) < dp(12)) {
                        beginCapture();
                    }
                    return true;
                default:
                    return false;
            }
        });

        windowManager.addView(bubble, bubbleParams);
        Toast.makeText(this, "Przycisk 📷 jest aktywny.", Toast.LENGTH_SHORT).show();
    }

    private void repositionBubble() {
        if (bubbleParams == null) return;
        DisplayMetrics dm = new DisplayMetrics();
        windowManager.getDefaultDisplay().getRealMetrics(dm);
        bubbleParams.x = Math.max(dp(8), dm.widthPixels - dp(84));
        bubbleParams.y = Math.max(dp(80), dm.heightPixels / 2 - dp(34));
        if (bubble != null && bubble.getWindowToken() != null) {
            try { windowManager.updateViewLayout(bubble, bubbleParams); } catch (Exception ignored) { }
        }
    }

    private void readDisplayMetrics() {
        DisplayMetrics dm = new DisplayMetrics();
        windowManager.getDefaultDisplay().getRealMetrics(dm);
        captureWidth = dm.widthPixels;
        captureHeight = dm.heightPixels;
        densityDpi = dm.densityDpi;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "MARBO YT Capture",
                    NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("Aktywne przechwytywanie ekranu");
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
        }
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this,
                0,
                open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);

        return builder
                .setContentTitle("MARBO YT Capture")
                .setContentText("Pływający przycisk aparatu jest aktywny")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .setContentIntent(pi)
                .setOngoing(true)
                .build();
    }

    private void releaseResources(boolean stopProjection) {
        captureRequested = false;
        if (bubble != null) {
            try { windowManager.removeView(bubble); } catch (Exception ignored) { }
            bubble = null;
        }
        if (virtualDisplay != null) {
            try { virtualDisplay.release(); } catch (Exception ignored) { }
            virtualDisplay = null;
        }
        if (imageReader != null) {
            try { imageReader.close(); } catch (Exception ignored) { }
            imageReader = null;
        }
        if (stopProjection && mediaProjection != null) {
            MediaProjection projection = mediaProjection;
            mediaProjection = null;
            try { projection.stop(); } catch (Exception ignored) { }
        } else {
            mediaProjection = null;
        }
    }

    @Override
    public void onDestroy() {
        releaseResources(true);
        if (imageThread != null) imageThread.quitSafely();
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
