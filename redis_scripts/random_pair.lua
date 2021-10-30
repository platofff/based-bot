-- 1 - conversation id
local msg_i = redis.call("zrandmember", KEYS[1], -1)[1]
local msg = redis.call("hmget", msg_i, "text", "answers")
local process = function ()
    if msg[2] == "" then
        local b, e = string.find(msg_i, ":.*.")
        local cur_i = tonumber(string.sub(msg_i, b + 1, e))
        local next_i = KEYS[1] .. ":" .. tostring(cur_i + 1)
        local next = redis.call("hget", next_i, "text")
        if next == nil then
            msg_i = KEYS[1] .. tostring(cur_i - 1)
            msg = redis.call("hmget", msg_i, "text", "answers")
            if msg[1] == nil then
                return ""
            end
            return process()
        end
        return msg[1] .. "\n" .. next
    else
        local answers = {}
        for answer in string.gmatch(example, "%S+") do
            table.insert(answers, answer)
        end
        return msg[1] .. "\n" .. redis.call("hget", "text", KEYS[1] .. ":" .. answers[math.random(#answers)])
    end
end
return process()