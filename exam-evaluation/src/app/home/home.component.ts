import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  uploading: boolean = false;
  score: number | null = null;
  selectedFile: File | null = null;

  constructor(private http: HttpClient, private authService: AuthService) {}

  onFileSelected(event: any) {
    const fileList: FileList = event.target.files;
    if (fileList.length > 0) {
      this.selectedFile = fileList[0];
    } else {
      this.selectedFile = null;
    }
  }

  uploadFile() {
    if (!this.selectedFile) {
      console.error('No file selected.');
      return;
    }

    this.uploading = true;
    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.authService.getScore(this.selectedFile).subscribe(
      response => {
        this.score = response.score;
        this.uploading = false;
      },
      error => {
        console.error('Error uploading file:', error);
        this.uploading = false;
      }
    );
  }
}
