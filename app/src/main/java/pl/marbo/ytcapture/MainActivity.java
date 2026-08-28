package pl.marbo.ytcapture;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int REQ_OVERLAY = 1001;
    private static final int REQ_CAPTURE = 1002;

    private EditText queryInput;
    private TextView statusText;
    private MediaProjectionManager projectionManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        projectionManager = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        buildUi();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(245, 247, 246));

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(22), dp(26), dp(22), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
                ScrollView.LayoutParams.MATCH_PARENT,
                ScrollView.LayoutParams.WRAP_CONTENT));

        TextView title = new TextView(this);
        title.setText("MARBO YT Capture");
        title.setTextSize(28);
        title.setTextColor(Color.rgb(20, 20, 20));
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        root.addView(title, lpMatch(0, 0, 0, 8));

        TextView subtitle = new TextView(this);
        subtitle.setText("Wyszukaj film w YouTube, włącz pełny ekran i użyj pływającego przycisku aparatu, aby zapisać aktualnie widoczny obraz do galerii.");
        subtitle.setTextSize(15);
        subtitle.setTextColor(Color.rgb(80, 88, 84));
        subtitle.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(subtitle, lpMatch(0, 0, 0, 24));

        queryInput = new EditText(this);
        queryInput.setHint("Tytuł filmu lub link YouTube");
        queryInput.setTextSize(17);
        queryInput.setSingleLine(true);
        queryInput.setPadding(dp(14), dp(12), dp(14), dp(12));
        queryInput.setBackground(rounded(Color.WHITE, Color.rgb(205, 211, 208), 12, 1));
        root.addView(queryInput, lpMatch(0, 0, 0, 12));

        Button search = makeButton("SZUKAJ W YOUTUBE", Color.rgb(229, 57, 53), Color.WHITE);
        search.setOnClickListener(v -> searchYouTube());
        root.addView(search, lpMatch(0, 0, 0, 10));

        Button openLink = makeButton("OTWÓRZ LINK", Color.rgb(35, 40, 38), Color.WHITE);
        openLink.setOnClickListener(v -> openEnteredLink());
        root.addView(openLink, lpMatch(0, 0, 0, 22));

        TextView step = new TextView(this);
        step.setText("Przed robieniem zrzutów:");
        step.setTextSize(18);
        step.setTextColor(Color.BLACK);
        step.setTypeface(null, android.graphics.Typeface.BOLD);
        root.addView(step, lpMatch(0, 0, 0, 10));

        Button enable = makeButton("WŁĄCZ PRZYCISK APARATU", Color.rgb(39, 174, 96), Color.WHITE);
        enable.setOnClickListener(v -> prepareCapture());
        root.addView(enable, lpMatch(0, 0, 0, 10));

        Button stop = makeButton("ZATRZYMAJ PRZYCISK APARATU", Color.rgb(95, 103, 99), Color.WHITE);
        stop.setOnClickListener(v -> {
            Intent i = new Intent(this, CaptureService.class);
            i.setAction(CaptureService.ACTION_STOP);
            startService(i);
            statusText.setText("Przycisk aparatu zatrzymany.");
        });
        root.addView(stop, lpMatch(0, 0, 0, 18));

        statusText = new TextView(this);
        statusText.setText("Najpierw włącz przycisk aparatu. Android poprosi o zgodę na nakładkę i przechwytywanie ekranu.");
        statusText.setTextSize(14);
        statusText.setTextColor(Color.rgb(65, 72, 68));
        statusText.setPadding(dp(14), dp(12), dp(14), dp(12));
        statusText.setBackground(rounded(Color.rgb(232, 241, 236), Color.TRANSPARENT, 10, 0));
        root.addView(statusText, lpMatch(0, 0, 0, 18));

        TextView note = new TextView(this);
        note.setText("Uwaga: aplikacja używa oficjalnego systemowego przechwytywania ekranu Android. Materiały chronione przez DRM lub blokadę przechwytywania mogą zapisać się jako czarny obraz — aplikacja nie omija takich zabezpieczeń.");
        note.setTextSize(12);
        note.setTextColor(Color.rgb(105, 112, 108));
        root.addView(note, lpMatch(0, 0, 0, 0));

        setContentView(scroll);
    }

    private void searchYouTube() {
        String q = queryInput.getText().toString().trim();
        if (q.isEmpty()) {
            Toast.makeText(this, "Wpisz tytuł filmu.", Toast.LENGTH_SHORT).show();
            return;
        }
        Uri uri = Uri.parse("https://www.youtube.com/results").buildUpon()
                .appendQueryParameter("search_query", q)
                .build();
        openYouTube(uri);
    }

    private void openEnteredLink() {
        String value = queryInput.getText().toString().trim();
        if (value.isEmpty()) {
            Toast.makeText(this, "Wklej link YouTube.", Toast.LENGTH_SHORT).show();
            return;
        }
        if (!value.startsWith("http://") && !value.startsWith("https://")) {
            searchYouTube();
            return;
        }
        openYouTube(Uri.parse(value));
    }

    private void openYouTube(Uri uri) {
        Intent yt = new Intent(Intent.ACTION_VIEW, uri);
        yt.setPackage("com.google.android.youtube");
        PackageManager pm = getPackageManager();
        if (yt.resolveActivity(pm) == null) {
            yt.setPackage(null);
        }
        try {
            startActivity(yt);
        } catch (Exception e) {
            Toast.makeText(this, "Nie udało się otworzyć YouTube.", Toast.LENGTH_LONG).show();
        }
    }

    private void prepareCapture() {
        if (!Settings.canDrawOverlays(this)) {
            statusText.setText("Zezwól MARBO YT Capture na wyświetlanie nad innymi aplikacjami, a potem wróć tutaj.");
            Intent overlay = new Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getPackageName()));
            startActivityForResult(overlay, REQ_OVERLAY);
            return;
        }
        requestScreenCapture();
    }

    private void requestScreenCapture() {
        statusText.setText("Potwierdź systemową zgodę na przechwytywanie ekranu.");
        startActivityForResult(projectionManager.createScreenCaptureIntent(), REQ_CAPTURE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQ_OVERLAY) {
            if (Settings.canDrawOverlays(this)) {
                requestScreenCapture();
            } else {
                statusText.setText("Brak zgody na pływający przycisk. Naciśnij WŁĄCZ ponownie.");
            }
            return;
        }

        if (requestCode == REQ_CAPTURE) {
            if (resultCode != RESULT_OK || data == null) {
                statusText.setText("Nie udzielono zgody na przechwytywanie ekranu.");
                return;
            }

            Intent service = new Intent(this, CaptureService.class);
            service.putExtra(CaptureService.EXTRA_RESULT_CODE, resultCode);
            service.putExtra(CaptureService.EXTRA_RESULT_DATA, data);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(service);
            } else {
                startService(service);
            }
            statusText.setText("Przycisk aparatu jest aktywny. Otwórz YouTube, włącz film na pełnym ekranie i naciśnij 📷.");
        }
    }

    private Button makeButton(String text, int background, int foreground) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(15);
        b.setTextColor(foreground);
        b.setAllCaps(false);
        b.setGravity(Gravity.CENTER);
        b.setPadding(dp(12), dp(13), dp(12), dp(13));
        b.setBackground(rounded(background, Color.TRANSPARENT, 12, 0));
        return b;
    }

    private GradientDrawable rounded(int fill, int stroke, int radiusDp, int strokeDp) {
        GradientDrawable gd = new GradientDrawable();
        gd.setColor(fill);
        gd.setCornerRadius(dp(radiusDp));
        if (strokeDp > 0) {
            gd.setStroke(dp(strokeDp), stroke);
        }
        return gd;
    }

    private LinearLayout.LayoutParams lpMatch(int l, int t, int r, int b) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        p.setMargins(dp(l), dp(t), dp(r), dp(b));
        return p;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
