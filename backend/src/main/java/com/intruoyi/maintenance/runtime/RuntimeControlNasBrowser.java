package com.intruoyi.maintenance.runtime;

import com.hierynomus.msfscc.fileinformation.FileIdBothDirectoryInformation;
import com.hierynomus.msfscc.FileAttributes;
import com.hierynomus.smbj.SMBClient;
import com.hierynomus.smbj.auth.AuthenticationContext;
import com.hierynomus.smbj.connection.Connection;
import com.hierynomus.smbj.session.Session;
import com.hierynomus.smbj.share.DiskShare;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Comparator;
import java.util.List;

@Component
public class RuntimeControlNasBrowser {

    public List<NasEntry> listDirectories(NasConfig config) {
        requireText(config.server(), "NAS server");
        requireText(config.share(), "NAS share");
        requireText(config.username(), "NAS username");
        requireText(config.password(), "NAS password");
        requireText(config.root(), "NAS root");
        try (SMBClient client = new SMBClient(); Connection connection = client.connect(config.server())) {
            AuthenticationContext authentication = new AuthenticationContext(
                    config.username(), config.password().toCharArray(), blankToEmpty(config.domain()));
            Session session = connection.authenticate(authentication);
            try (DiskShare share = (DiskShare) session.connectShare(config.share())) {
                return share.list(config.root()).stream()
                        .filter(RuntimeControlNasBrowser::isRealDirectory)
                        .map(item -> new NasEntry(item.getFileName(), config.root() + "/" + item.getFileName()))
                        .sorted(Comparator.comparing(NasEntry::name).reversed())
                        .toList();
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("NAS 浏览失败: " + config.server() + "/" + config.share(), ex);
        }
    }

    private static boolean isRealDirectory(FileIdBothDirectoryInformation item) {
        String name = item.getFileName();
        long attributes = item.getFileAttributes();
        return !".".equals(name) && !"..".equals(name)
                && (attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY.getValue()) != 0;
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new RuntimeControlException(name + " is required");
        }
    }

    private static String blankToEmpty(String value) {
        return value == null ? "" : value;
    }

    public record NasConfig(
            String server,
            String share,
            String username,
            String password,
            String domain,
            String root
    ) {
    }

    public record NasEntry(String name, String path) {
    }
}
