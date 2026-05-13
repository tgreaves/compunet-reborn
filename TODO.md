# TODO

## Bugs

- **@last_byte timing issue with multi-packet DIR responses**: When a directory response is split across two packets (>200 bytes), the `@last_byte` NMI buffer peek may not find the second packet's `$01` start marker in time. The 4K-iteration wait helps but is not a guaranteed fix. The root cause is that VICE's socket polling introduces variable latency between packets. Current workaround: keep directory responses under 200 bytes. Proper fix: either increase the wait further (adds latency to single-packet responses) or redesign `@last_byte` to always return CLC and handle end-of-stream purely in `@need_new_packet`.
