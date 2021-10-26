local r = {}
local prefix = KEYS[1] .. ":"
for i = 2, #KEYS do
    local res = redis.call("smembers", KEYS[i])
    for j = 1, #res do
        if string.sub(res[j], 1, #prefix) == prefix then
            table.insert(r, res[j])
        end
    end
end
return r

