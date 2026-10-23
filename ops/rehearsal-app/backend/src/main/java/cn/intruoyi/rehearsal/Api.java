package cn.intruoyi.rehearsal;

import jakarta.servlet.http.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api")
public class Api {
    final LabService service;
    public Api(LabService service){this.service=service;}
    record Login(@NotNull Long tenantId,@NotBlank @Size(max=64) String username,@NotBlank @Size(max=72) String password){}
    record Edit(@NotBlank @Size(max=120) String title,@NotNull @Size(max=2000) String content){}
    @PostMapping("/login") public Map<String,Object> login(@Valid @RequestBody Login input,HttpServletResponse response){
        String token=service.login(input.tenantId(),input.username(),input.password());
        response.addHeader("Set-Cookie",ResponseCookie.from("lab_session",token).httpOnly(true).sameSite("Strict").path("/api").maxAge(28800).build().toString());return Map.of("tenantId",input.tenantId(),"username",input.username());
    }
    @GetMapping("/me") public Map<String,Object> me(@RequestAttribute LabService.Actor actor){return Map.of("tenantId",actor.tenantId(),"tenantName",actor.tenantName(),"username",actor.username(),"server",System.getenv("LAB_SERVER"),"releaseTag",System.getenv("RELEASE_TAG"));}
    @PostMapping("/logout") public void logout(HttpServletRequest request,HttpServletResponse response){service.logout(WebConfig.token(request));response.addHeader("Set-Cookie",ResponseCookie.from("lab_session","").httpOnly(true).sameSite("Strict").path("/api").maxAge(0).build().toString());}
    @GetMapping("/records") public List<Entry> records(@RequestAttribute LabService.Actor actor){return service.list(actor);}
    @PostMapping("/records") public Entry create(@RequestAttribute LabService.Actor actor,@Valid @RequestBody Edit input){return service.save(actor,null,input.title(),input.content());}
    @PutMapping("/records/{id}") public Entry edit(@RequestAttribute LabService.Actor actor,@PathVariable long id,@Valid @RequestBody Edit input){return service.save(actor,id,input.title(),input.content());}
    @DeleteMapping("/records/{id}") public void delete(@RequestAttribute LabService.Actor actor,@PathVariable long id){service.delete(actor,id);}
    @GetMapping("/records/{id}/attachments") public List<Map<String,Object>> attachments(@RequestAttribute LabService.Actor actor,@PathVariable long id){return service.attachments(actor,id);}
    @PostMapping("/records/{id}/attachments") public Map<String,Object> upload(@RequestAttribute LabService.Actor actor,@PathVariable long id,@RequestParam("file") MultipartFile file) throws Exception {
        if(file.isEmpty()||file.getSize()>5*1024*1024)throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"附件需为 1 字节至 5 MB");
        return service.upload(actor,id,file.getOriginalFilename(),file.getBytes());
    }
    @GetMapping("/attachments/{id}") public ResponseEntity<byte[]> download(@RequestAttribute LabService.Actor actor,@PathVariable String id) throws Exception {
        var attachment=service.attachment(actor,id);
        return ResponseEntity.ok().header("Content-Disposition",ContentDisposition.attachment().filename((String)attachment.get("name"),StandardCharsets.UTF_8).build().toString()).contentType(MediaType.APPLICATION_OCTET_STREAM).body(service.download(actor,id));
    }
    @DeleteMapping("/attachments/{id}") public void deleteAttachment(@RequestAttribute LabService.Actor actor,@PathVariable String id) throws Exception {service.deleteAttachment(actor,id);}
}
