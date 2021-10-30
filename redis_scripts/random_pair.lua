--[[
Аргументы:
1: id беседы в БД (peer_id - 2000000000)
Возвращает:
1: строка, содержащая текст 2 сообщений, второе является ответом на первое. Сообщения разделены символом переноса строки '\n'
--]]
local msg_i = redis.call("zrandmember", KEYS[1], -1)[1]
local msg = redis.call("hmget", msg_i, "text", "answers")
local process = function ()
    if msg[2] == "" then
        local b, e = string.find(msg_i, ":.*.")
        local cur_i = tonumber(string.sub(msg_i, b + 1, e))
        local next_i = KEYS[1] .. ":" .. tostring(cur_i + 1)
        local next = redis.call("hget", next_i, "text")
        if next == false then
            msg_i = KEYS[1] .. tostring(cur_i - 1)
            msg = redis.call("hmget", msg_i, "text", "answers")
            if msg[1] == false then
                return ""
            end
            return process()
        end
        return msg[1] .. "\n" .. next
    else
        local answers = {}
        for answer in string.gmatch(msg[2], "%S+") do
            table.insert(answers, answer)
        end
        local answer = answers[math.random(#answers)]
        return msg[1] .. "\n" .. redis.call("hget", redis.call("zrange", KEYS[1], answer, answer, "byscore")[1], "text")
    end
end
return process()