package cn.intruoyi.rehearsal;
import jakarta.servlet.http.*;
import java.net.URI;
import java.util.Arrays;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.FORBIDDEN;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    final LabService service;
    public WebConfig(LabService service){this.service=service;}
    static String token(HttpServletRequest req){return req.getCookies()==null?null:Arrays.stream(req.getCookies()).filter(c->c.getName().equals("lab_session")).map(Cookie::getValue).findFirst().orElse(null);}
    public void addInterceptors(InterceptorRegistry registry){registry.addInterceptor(new HandlerInterceptor(){
        public boolean preHandle(HttpServletRequest req,HttpServletResponse res,Object handler){
            if(!req.getMethod().equals("GET")&&!req.getMethod().equals("HEAD")){
                String origin=req.getHeader("Origin");
                if(origin==null||!URI.create(origin).getAuthority().equals(req.getHeader("Host")))throw new ResponseStatusException(FORBIDDEN,"请求来源不匹配");
            }
            if(!req.getRequestURI().equals("/api/login"))req.setAttribute("actor",service.authenticate(token(req)));return true;
        }
    }).addPathPatterns("/api/**");}
}
