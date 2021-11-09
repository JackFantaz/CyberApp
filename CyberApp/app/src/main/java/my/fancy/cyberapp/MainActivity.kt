package my.fancy.cyberapp

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.browser.customtabs.CustomTabsIntent
import org.pytorch.IValue
import org.pytorch.Module
import org.pytorch.torchvision.TensorImageUtils
import java.io.*
import kotlin.math.ceil
import kotlin.math.pow
import kotlin.math.round

const val REQUEST_CODE = 1
const val CLASSES_FILE = "classes.txt"
const val MODEL_FILE = "resnet_full_aware_i8.ptl"
const val IMAGE_SIZE = 224

class MainActivity : AppCompatActivity() {

    private lateinit var module: Module
    private lateinit var classes: List<String>
    private lateinit var button: Button
    private lateinit var imageView: ImageView
    private lateinit var textView: TextView

    private fun assetPath(name: String): String {
        val context = this
        val file = File(this.cacheDir, name)
        if (!file.exists() || file.length() <= 0) {
            val input = context.assets.open(name)
            val output = FileOutputStream(file)
            val buffer = ByteArray(4 * 1025)
            var read = input.read(buffer)
            while (read != -1) {
                output.write(buffer, 0, read)
                read = input.read(buffer)
            }
            output.flush()
        }
        return file.absolutePath
    }

    private fun setup() {
        Log.w("CyberApp", "setup()")
        try {
            module = Module.load(this.assetPath(MODEL_FILE))
            classes = BufferedReader(InputStreamReader(this.assets.open(CLASSES_FILE), Charsets.ISO_8859_1)).readLines()
            button = this.findViewById(R.id.button)
            button.setOnClickListener { takePicture() }
            imageView = this.findViewById(R.id.imageView)
            textView = this.findViewById(R.id.textView)
            textView.text = ""
        } catch (e: Exception) {
            Log.e("CyberApp.setup", e.message, e)
            Toast.makeText(this, e.message, Toast.LENGTH_SHORT).show()
        }
    }

    private fun padScale(bitmap: Bitmap, size: Int): Bitmap {
        val width = bitmap.width
        val height = bitmap.height
        val targetHeight: Int
        val targetWidth: Int
        val paddingTop: Int
        val paddingLeft: Int
        if (height >= width) {
            targetHeight = size
            targetWidth = round(1.0 * width / height * targetHeight).toInt()
            paddingTop = 0
            paddingLeft = ceil(1.0 * (targetHeight - targetWidth) / 2).toInt()
        } else {
            targetWidth = size
            targetHeight = round(1.0 * height / width * targetWidth).toInt()
            paddingTop = ceil(1.0 * (targetWidth - targetHeight) / 2).toInt()
            paddingLeft = 0
        }
        val scaled = Bitmap.createScaledBitmap(bitmap, targetWidth, targetHeight, true)
        val final = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(final)
        canvas.drawARGB(255, 0, 0, 0)
        canvas.drawBitmap(scaled, paddingLeft.toFloat(), paddingTop.toFloat(), null)
        return final
    }

    private fun takePicture() {
        Log.w("CyberApp", "takePicture()")
        try {
            val takePictureIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            startActivityForResult(takePictureIntent, REQUEST_CODE)
        } catch (e: Exception) {
            Log.e("CyberApp.takePicture", e.message, e)
            Toast.makeText(this, e.message, Toast.LENGTH_SHORT).show()
        }
    }

    private fun evaluatePicture(bitmap: Bitmap): List<String> {
        val input = TensorImageUtils.bitmapToFloat32Tensor(bitmap, TensorImageUtils.TORCHVISION_NORM_MEAN_RGB, TensorImageUtils.TORCHVISION_NORM_STD_RGB)
        val output = module.forward(IValue.from(input)).toTensor()
        val scores = output.dataAsFloatArray.asList()
        val id = scores.indexOf(scores.maxOrNull())
        val prediction = classes[id].split("\t").toMutableList()
        val softmax = Math.E.pow(scores.maxOrNull()!!.toDouble()) / scores.sumOf { Math.E.pow(it.toDouble()) }
        val percentage = softmax * 100
        prediction.add(String.format("%.1f%%", percentage))
        return prediction
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        Log.w("CyberApp", "onActivityResult()")
        try {
            if (requestCode == REQUEST_CODE && resultCode == Activity.RESULT_OK) {
                val bitmap = data!!.extras!!.get("data") as Bitmap
                val resized = padScale(bitmap, IMAGE_SIZE)
                imageView.setImageBitmap(resized)
                val prediction = evaluatePicture(resized)
                val title = prediction[1].uppercase()
                val author = prediction[2].uppercase()
                val link = "http://nilf.it/${prediction[0].substring(4, 10)}"
                val confidence = prediction[3]
                textView.text = "$title\nby $author\n$link\nconfidence $confidence"
                val builder = CustomTabsIntent.Builder()
                val intent = builder.build()
                intent.launchUrl(this, Uri.parse(link))
            } else {
                super.onActivityResult(requestCode, resultCode, data)
            }
        } catch (e: Exception) {
            Log.e("CyberApp.onActivityResult", e.message, e)
            Toast.makeText(this, e.message, Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        this.setContentView(R.layout.activity_main)
        this.setup()
    }

}
