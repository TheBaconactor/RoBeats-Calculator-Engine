-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_4 ]]
        local v_u_5 = {}
        local v_u_6 = v_u_1:new()
        local v_u_7 = v_u_1:new()
        local function _() --[[ Name: cons ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (copy 3): v_u_5, (ref 4): v_u_4 ]]
            if v_u_2:is_dev_build() then
                spawn(function() end)
            end;
        end;
        v_u_5.get_audio_length = function(_, p8) --[[ Name: get_audio_length ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_7 ]]
            if v_u_6:contains(p8) then
                return true, v_u_6:get(p8).Length;
            end;
            if v_u_7:contains(p8) then
                return false, 0;
            end;
            local l_Sound_0 = Instance.new("Sound", game.ServerStorage)
            l_Sound_0.SoundId = p8
            l_Sound_0.Volume = 0
            l_Sound_0.Name = string.format("SoundLoad(%s)", p8)
            v_u_7:add(p8, l_Sound_0)
            return false, 0;
        end;
        v_u_5.update = function(_, _) --[[ Name: update ]] --[[ Line: 60 ]]
            --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_6 ]]
            if v_u_7:count() ~= 0 then
                local v9 = v_u_7:key_list()
                for v10 = 1, v9:count() do
                    local v11 = v9:get(v10)
                    local v12 = v_u_7:get(v11)
                    if v12.IsLoaded then
                        v_u_6:add(v11, {
                            ["Length"] = v12.TimeLength
                        })
                        v12:Destroy()
                        v_u_7:remove(v11)
                    end;
                end;
            end;
        end;
        if v_u_2:is_dev_build() then
            spawn(function() end)
        end;
        return v_u_5;
    end
};
