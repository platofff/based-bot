--[[
Аргументы:
1: id беседы в БД (peer_id - 2000000000)
2+: ключевые слова для поиска
Возвращает:
1: массив, включающий id всех подходящих сообщений в db4, могут повторяться
--]]
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

