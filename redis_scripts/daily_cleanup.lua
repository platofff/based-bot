--[[
Аргументы:
1: максимальный объём в байтах, занимаемый одной беседой в БД
2+: peer_id бесед без ограничений на объём
--]]
local LIMIT = tonumber(KEYS[1])
local unlimited = {}
for i = 2, #KEYS do
    table.insert(unlimited, tonumber(KEYS[i]))
end
redis.call("select", 3)
local conversations = redis.call("smembers", "mstore")
redis.call("select", 4)
for i = 1, #conversations do
    conversations[i] = conversations[i] - 2000000000
    if unlimited[conversations[i]] == nil then
        local messages = redis.call("zrange", conversations[i], "-inf", "+inf", "byscore", "withscores")
        local total_usage = 0
        local messages_text = {}
        local messages_indexes = {}
        for j = 1, #messages do
            if j % 2 == 1 then
                table.insert(messages_text, messages[j])
            else
                table.insert(messages_indexes, conversations[i] .. ":" .. messages[j])
            end
        end
        local messages_usage = {}
        for j = 1, #messages_text do
            messages_usage[j] = redis.call("memory", "usage", messages_text[j])
            total_usage = total_usage + messages_usage[j]
        end
        local del_index = 0
        while total_usage > LIMIT do
            del_index = del_index + 1
            total_usage = total_usage - messages_usage[del_index]
        end
        if del_index ~= 0 then
            redis.call("select", 5)
            local keywords = redis.call("keys", "*")
            for j = 1, #keywords do
                redis.call("srem", keywords[j], unpack(messages_indexes, 1, del_index))
            end
            redis.call("select", 4)
            redis.call("del", unpack(messages_text, 1, del_index))
            for j = 1, del_index do
                redis.call("zpopmin", conversations[i])
            end
        end
    end
end