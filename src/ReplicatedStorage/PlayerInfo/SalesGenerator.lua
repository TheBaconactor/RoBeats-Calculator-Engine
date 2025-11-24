-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_19 = {
    ["generate_day_sales"] = function(_) --[[ Name: generate_day_sales ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3 ]]
        local v4 = v_u_1:singleton()
        local v5 = v4:all_keys()
        local v6 = v_u_2:new()
        local v7 = v_u_2:new()
        local v8 = v_u_2:new()
        local v9 = v_u_2:new()
        for v10 = 1, v5:count() do
            local v11 = v5:get(v10)
            if v4:key_get_audiomod(v11) == v_u_1.MOD_NORMAL then
                local v12 = v4:get_difficulty_for_key(v11)
                if v12 <= 5 then
                    v6:push_back(v11)
                elseif v12 <= 8 then
                    v7:push_back(v11)
                elseif v12 <= 13 then
                    v8:push_back(v11)
                else
                    v9:push_back(v11)
                end;
            end;
        end;
        local v13 = {}
        local v14 = 1
        for _ = 1, 10 do
            local v15 = v_u_3:rand_rangef(0, 100)
            local v16, v17
            if v15 < 40 then
                v16 = v6
                v17 = 40
            elseif v15 < 65 then
                v16 = v7
                v17 = 100
            elseif v15 < 85 then
                v16 = v8
                v17 = 175
            else
                v16 = v9
                v17 = 250
            end;
            if v16:count() > 0 then
                local v18 = v16:random()
                v16:remove(v18)
                v13[#v13 + 1] = {
                    ["SaleId"] = v14,
                    ["SongKey"] = v18,
                    ["PriceType"] = 0,
                    ["PriceValue"] = v17,
                    ["SongName"] = v4:get_title_for_key(v18)
                }
                v14 = v14 + 1
            end;
        end;
        return v13;
    end
}
v_u_19.generate_sales = function(_) --[[ Name: generate_sales ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_19 ]]
    local v20 = {}
    for v21 = 81, 95 do
        local v22 = v_u_19:generate_day_sales()
        v20[#v20 + 1] = {
            ["SaleDay"] = v21,
            ["AvailableItems"] = v22
        }
    end;
    print(game:GetService("HttpService"):JSONEncode(v20))
end;
return v_u_19;
