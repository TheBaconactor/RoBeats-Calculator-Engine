-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:05 PM
-- Time elapsed: 38 milliseconds

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = {
    ["TitleInfoBase"] = {}
}
v_u_4.TitleInfoBase.new = function(_) --[[ Name: new ]] --[[ Line: 9 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v5 = {
        ["is_visible"] = function(_) --[[ Name: is_visible ]] --[[ Line: 14 ]]
            return true;
        end,
        ["get_description"] = function(_) --[[ Name: get_description ]] --[[ Line: 15 ]]
            return "";
        end,
        ["is_vip_only"] = function(_) --[[ Name: is_vip_only ]] --[[ Line: 18 ]]
            return false;
        end,
        ["is_guild_title"] = function(_) --[[ Name: is_guild_title ]] --[[ Line: 19 ]]
            return false;
        end
    }
    local v_u_6 = -1
    v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 12 ]]
        --[[ Upvalues: (ref 1): v_u_3 ]]
        v_u_3:errf("TitleDatabase.TitleInfoBase must implement get_name")
    end;
    v5.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 13 ]]
        --[[ Upvalues: (ref 1): v_u_3 ]]
        v_u_3:errf("TitleDatabase.TitleInfoBase must implement get_color")
    end;
    v5.set_title_id = function(_, p7) --[[ Name: set_title_id ]] --[[ Line: 16 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        v_u_6 = p7
    end;
    v5.get_title_id = function(_) --[[ Name: get_title_id ]] --[[ Line: 17 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        return v_u_6;
    end;
    return v5;
end;
local v_u_9 = (function() --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2 ]]
    local v8 = v_u_4.TitleInfoBase:new()
    v8.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 26 ]]
        return "(None)";
    end;
    v8.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        return v_u_2:color3(255, 255, 255);
    end;
    v8.is_visible = function(_) --[[ Name: is_visible ]] --[[ Line: 28 ]]
        return false;
    end;
    v8.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 29 ]]
        return "No title displayed.";
    end;
    return v8;
end)()
v_u_4.new = function(_) --[[ Name: new ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_9, (copy 3): v_u_4, (copy 4): v_u_2 ]]
    local v_u_16 = {
        ["get_default_title_id"] = function(_) --[[ Name: get_default_title_id ]] --[[ Line: 714 ]]
            return 0;
        end,
        ["get_title_name_for_id"] = function(p10, p11) --[[ Name: get_title_name_for_id ]] --[[ Line: 726 ]]
            return p10:get_title_for_id(p11):get_name();
        end,
        ["get_title_color_for_id"] = function(p12, p13) --[[ Name: get_title_color_for_id ]] --[[ Line: 727 ]]
            return p12:get_title_for_id(p13):get_color();
        end,
        ["get_title_active_for_id"] = function(p14, p15) --[[ Name: get_title_active_for_id ]] --[[ Line: 728 ]]
            return p14:get_title_for_id(p15):get_active();
        end,
        ["get_guild_title_id"] = function(_) --[[ Name: get_guild_title_id ]] --[[ Line: 741 ]]
            return 27;
        end
    }
    local v_u_17 = v_u_1:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_9, (ref 3): v_u_4, (ref 4): v_u_2 ]]
        v_u_16:add_title_for_id(0, v_u_9)
        v_u_16:add_title_for_id(1, ((function() --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v18 = v_u_4.TitleInfoBase:new()
            v18.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 43 ]]
                return "Contributor";
            end;
            v18.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 44 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(0, 255, 0);
            end;
            v18.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 45 ]]
                return "Given to contributors to RoBeats.";
            end;
            return v18;
        end)()))
        v_u_16:add_title_for_id(2, ((function() --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v19 = v_u_4.TitleInfoBase:new()
            v19.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 51 ]]
                return "Remixer";
            end;
            v19.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 52 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(177, 251, 255);
            end;
            v19.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 53 ]]
                return "Given to mappers that contributed to RoBeats: Remixed.";
            end;
            return v19;
        end)()))
        v_u_16:add_title_for_id(3, ((function() --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v20 = v_u_4.TitleInfoBase:new()
            v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 59 ]]
                return "Mapper";
            end;
            v20.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(150, 150, 230);
            end;
            v20.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 61 ]]
                return "Given to players who have successfully had a submitted map accepted and moved to live.";
            end;
            return v20;
        end)()))
        v_u_16:add_title_for_id(4, ((function() --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v21 = v_u_4.TitleInfoBase:new()
            v21.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 67 ]]
                return "Debugger";
            end;
            v21.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(177, 251, 255);
            end;
            v21.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 69 ]]
                return "Given to players who have reported critical bugs.";
            end;
            return v21;
        end)()))
        v_u_16:add_title_for_id(5, ((function() --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v22 = v_u_4.TitleInfoBase:new()
            v22.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 75 ]]
                return "Champion";
            end;
            v22.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 76 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(254, 69, 245);
            end;
            v22.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 77 ]]
                return "Given to players who have come in 1st place in a weekly leaderboard.";
            end;
            return v22;
        end)()))
        v_u_16:add_title_for_id(6, ((function() --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v23 = v_u_4.TitleInfoBase:new()
            v23.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 83 ]]
                return "Challenger";
            end;
            v23.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 84 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(248, 112, 245);
            end;
            v23.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 85 ]]
                return "Given to players who have come in the top 20 in a weekly leaderboard.";
            end;
            return v23;
        end)()))
        v_u_16:add_title_for_id(7, ((function() --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v24 = v_u_4.TitleInfoBase:new()
            v24.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 91 ]]
                return "Contender";
            end;
            v24.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 92 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(241, 162, 246);
            end;
            v24.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 93 ]]
                return "Given to players who have come in the top 50 in a weekly leaderboard.";
            end;
            return v24;
        end)()))
        v_u_16:add_title_for_id(8, ((function() --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v25 = v_u_4.TitleInfoBase:new()
            v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 99 ]]
                return "Participant";
            end;
            v25.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(234, 208, 247);
            end;
            v25.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 101 ]]
                return "Given to players who have come in the top 200 in a weekly leaderboard.";
            end;
            return v25;
        end)()))
        v_u_16:add_title_for_id(9, ((function() --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v26 = v_u_4.TitleInfoBase:new()
            v26.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 107 ]]
                return "VIP";
            end;
            v26.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 108 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(241, 200, 30);
            end;
            v26.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 109 ]]
                return "Given to players who are Robeats VIPs.";
            end;
            v26.is_vip_only = function(_) --[[ Name: is_vip_only ]] --[[ Line: 110 ]]
                return true;
            end;
            return v26;
        end)()))
        v_u_16:add_title_for_id(10, ((function() --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v27 = v_u_4.TitleInfoBase:new()
            v27.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 116 ]]
                return "Challenge Master";
            end;
            v27.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 117 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v27.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 118 ]]
                return "Given to players who complete the Season 1 Challenge Pass.";
            end;
            return v27;
        end)()))
        v_u_16:add_title_for_id(11, ((function() --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v28 = v_u_4.TitleInfoBase:new()
            v28.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 124 ]]
                return "Challenge Master";
            end;
            v28.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 125 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v28.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 126 ]]
                return "Given to players who complete the Season 2 Challenge Pass.";
            end;
            return v28;
        end)()))
        v_u_16:add_title_for_id(12, ((function() --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v29 = v_u_4.TitleInfoBase:new()
            v29.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 132 ]]
                return "Challenge Master";
            end;
            v29.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 133 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v29.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 134 ]]
                return "Given to players who complete the Season 3 Challenge Pass.";
            end;
            return v29;
        end)()))
        v_u_16:add_title_for_id(13, ((function() --[[ Line: 138 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v30 = v_u_4.TitleInfoBase:new()
            v30.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 140 ]]
                return "Challenge Master";
            end;
            v30.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 141 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v30.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 142 ]]
                return "Given to players who complete the Season 4 Challenge Pass.";
            end;
            return v30;
        end)()))
        v_u_16:add_title_for_id(14, ((function() --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v31 = v_u_4.TitleInfoBase:new()
            v31.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 148 ]]
                return "Challenge Master";
            end;
            v31.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 149 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v31.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 150 ]]
                return "Given to players who complete the Season 5 Challenge Pass.";
            end;
            return v31;
        end)()))
        v_u_16:add_title_for_id(15, ((function() --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v32 = v_u_4.TitleInfoBase:new()
            v32.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 156 ]]
                return "Challenge Master";
            end;
            v32.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 157 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v32.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 158 ]]
                return "Given to players who complete the Season 6 Challenge Pass.";
            end;
            return v32;
        end)()))
        v_u_16:add_title_for_id(16, ((function() --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v33 = v_u_4.TitleInfoBase:new()
            v33.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 164 ]]
                return "Robeats Beta Tester";
            end;
            v33.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 165 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 176, 130);
            end;
            v33.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 166 ]]
                return "Given to players that are Robeats BETA testers.";
            end;
            return v33;
        end)()))
        v_u_16:add_title_for_id(17, ((function() --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v34 = v_u_4.TitleInfoBase:new()
            v34.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 172 ]]
                return "Roblox Premium";
            end;
            v34.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 173 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(241, 200, 150);
            end;
            v34.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 174 ]]
                return "Given to players that have subscribed to Roblox Premium.";
            end;
            return v34;
        end)()))
        v_u_16:add_title_for_id(18, ((function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v35 = v_u_4.TitleInfoBase:new()
            v35.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 180 ]]
                return "RB Battles Secret Master";
            end;
            v35.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 181 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(200, 220, 200);
            end;
            v35.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 182 ]]
                return "Given to players that found the RB Battles secret.";
            end;
            return v35;
        end)()))
        v_u_16:add_title_for_id(19, ((function() --[[ Line: 186 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v36 = v_u_4.TitleInfoBase:new()
            v36.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 188 ]]
                return "Robeats Famous";
            end;
            v36.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 189 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(177, 251, 255);
            end;
            v36.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 190 ]]
                return "Given to people that are Robeats Famous.";
            end;
            return v36;
        end)()))
        v_u_16:add_title_for_id(20, ((function() --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v37 = v_u_4.TitleInfoBase:new()
            v37.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 196 ]]
                return "Music Producer";
            end;
            v37.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(177, 251, 255);
            end;
            v37.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 198 ]]
                return "Given to Music Producers that have contributed to Robeats.";
            end;
            return v37;
        end)()))
        v_u_16:add_title_for_id(21, ((function() --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v38 = v_u_4.TitleInfoBase:new()
            v38.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 204 ]]
                return "Silentroom Fan";
            end;
            v38.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 205 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(218, 230, 209);
            end;
            v38.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 206 ]]
                return "Fans of Silentroom.";
            end;
            return v38;
        end)()))
        v_u_16:add_title_for_id(22, ((function() --[[ Line: 210 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v39 = v_u_4.TitleInfoBase:new()
            v39.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 212 ]]
                return "Se-U-Ra Fan";
            end;
            v39.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 213 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(183, 120, 158);
            end;
            v39.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 214 ]]
                return "Fans of Se-U-Ra.";
            end;
            return v39;
        end)()))
        v_u_16:add_title_for_id(23, ((function() --[[ Line: 218 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v40 = v_u_4.TitleInfoBase:new()
            v40.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 220 ]]
                return "Monstercat Fan";
            end;
            v40.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 221 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(249, 160, 189);
            end;
            v40.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 222 ]]
                return "Fans of Monstercat.";
            end;
            return v40;
        end)()))
        v_u_16:add_title_for_id(24, ((function() --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v41 = v_u_4.TitleInfoBase:new()
            v41.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 228 ]]
                return "Chroma Fan";
            end;
            v41.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 229 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(221, 215, 205);
            end;
            v41.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 230 ]]
                return "Fans of Chroma.";
            end;
            return v41;
        end)()))
        v_u_16:add_title_for_id(25, ((function() --[[ Line: 234 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v42 = v_u_4.TitleInfoBase:new()
            v42.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 236 ]]
                return "Cametek Fan";
            end;
            v42.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 237 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(154, 255, 253);
            end;
            v42.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 238 ]]
                return "Fans of Cametek.";
            end;
            return v42;
        end)()))
        v_u_16:add_title_for_id(26, ((function() --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v43 = v_u_4.TitleInfoBase:new()
            v43.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 244 ]]
                return "ARForest Fan";
            end;
            v43.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 245 ]]
                return Color3.fromRGB(216, 167, 228);
            end;
            v43.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 246 ]]
                return "Fans of ARForest.";
            end;
            return v43;
        end)()))
        v_u_16:add_title_for_id(27, ((function() --[[ Line: 249 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v44 = v_u_4.TitleInfoBase:new()
            v44.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 251 ]]
                return "Team Title";
            end;
            v44.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 252 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 255, 255);
            end;
            v44.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 253 ]]
                return "Show off your team with this title.";
            end;
            v44.is_guild_title = function(_) --[[ Name: is_guild_title ]] --[[ Line: 254 ]]
                return true;
            end;
            return v44;
        end)()))
        v_u_16:add_title_for_id(28, ((function() --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v45 = v_u_4.TitleInfoBase:new()
            v45.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 259 ]]
                return "FNF Fan";
            end;
            v45.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 260 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(245, 224, 145);
            end;
            v45.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 261 ]]
                return "Fans of FNF.";
            end;
            return v45;
        end)()))
        v_u_16:add_title_for_id(29, ((function() --[[ Line: 264 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v46 = v_u_4.TitleInfoBase:new()
            v46.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 266 ]]
                return "Event Music Producer";
            end;
            v46.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 267 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(241, 45, 196);
            end;
            v46.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 268 ]]
                return "Given to event music producers.";
            end;
            return v46;
        end)()))
        v_u_16:add_title_for_id(30, ((function() --[[ Line: 271 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v47 = v_u_4.TitleInfoBase:new()
            v47.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 273 ]]
                return "Poppy Fanatic";
            end;
            v47.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 274 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(199, 206, 255);
            end;
            v47.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 275 ]]
                return "Fans of Poppy.";
            end;
            return v47;
        end)()))
        v_u_16:add_title_for_id(31, ((function() --[[ Line: 278 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v48 = v_u_4.TitleInfoBase:new()
            v48.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 280 ]]
                return "garlagan Fan";
            end;
            v48.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 281 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(247, 188, 240);
            end;
            v48.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 282 ]]
                return "Fans of garlagan.";
            end;
            return v48;
        end)()))
        v_u_16:add_title_for_id(32, ((function() --[[ Line: 285 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v49 = v_u_4.TitleInfoBase:new()
            v49.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 287 ]]
                return "naruto2413 Fan";
            end;
            v49.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 288 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(211, 247, 186);
            end;
            v49.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 289 ]]
                return "Fans of naruto2413.";
            end;
            return v49;
        end)()))
        v_u_16:add_title_for_id(33, ((function() --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v50 = v_u_4.TitleInfoBase:new()
            v50.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 294 ]]
                return "Creo Fan";
            end;
            v50.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 295 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 185, 134);
            end;
            v50.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 296 ]]
                return "Fans of Creo.";
            end;
            return v50;
        end)()))
        v_u_16:add_title_for_id(34, ((function() --[[ Line: 299 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v51 = v_u_4.TitleInfoBase:new()
            v51.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 301 ]]
                return "Dance Creator";
            end;
            v51.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 302 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(19, 88, 87);
            end;
            v51.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 303 ]]
                return "Creators of dances used ingame in Robeats.";
            end;
            return v51;
        end)()))
        v_u_16:add_title_for_id(35, ((function() --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v52 = v_u_4.TitleInfoBase:new()
            v52.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 308 ]]
                return "Halloween Herald";
            end;
            v52.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(211, 156, 255);
            end;
            v52.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 310 ]]
                return "Fans of Halloween.";
            end;
            return v52;
        end)()))
        v_u_16:add_title_for_id(36, ((function() --[[ Line: 313 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v53 = v_u_4.TitleInfoBase:new()
            v53.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 315 ]]
                return "Art Creator";
            end;
            v53.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 316 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(19, 88, 87);
            end;
            v53.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 317 ]]
                return "Creators of art used ingame in Robeats.";
            end;
            return v53;
        end)()))
        v_u_16:add_title_for_id(37, ((function() --[[ Line: 320 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v54 = v_u_4.TitleInfoBase:new()
            v54.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 322 ]]
                return "xi Fan";
            end;
            v54.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 323 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(130, 299, 239);
            end;
            v54.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 324 ]]
                return "Fans of xi.";
            end;
            return v54;
        end)()))
        v_u_16:add_title_for_id(38, ((function() --[[ Line: 327 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v55 = v_u_4.TitleInfoBase:new()
            v55.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 329 ]]
                return "James Landino Fan";
            end;
            v55.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 330 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(227, 157, 143);
            end;
            v55.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 331 ]]
                return "Fans of James Landino.";
            end;
            return v55;
        end)()))
        v_u_16:add_title_for_id(39, ((function() --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v56 = v_u_4.TitleInfoBase:new()
            v56.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 336 ]]
                return "F-777 Fan";
            end;
            v56.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 337 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(164, 224, 195);
            end;
            v56.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 338 ]]
                return "Fans of F-777.";
            end;
            return v56;
        end)()))
        v_u_16:add_title_for_id(40, ((function() --[[ Line: 341 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v57 = v_u_4.TitleInfoBase:new()
            v57.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 343 ]]
                return "Just Dance Fan";
            end;
            v57.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 344 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(165, 224, 250);
            end;
            v57.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 345 ]]
                return "Fans of Just Dance.";
            end;
            return v57;
        end)()))
        v_u_16:add_title_for_id(41, ((function() --[[ Line: 348 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v58 = v_u_4.TitleInfoBase:new()
            v58.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 350 ]]
                return "dark cat Fan";
            end;
            v58.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 351 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(184, 170, 230);
            end;
            v58.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 352 ]]
                return "Fans of dark cat.";
            end;
            return v58;
        end)()))
        v_u_16:add_title_for_id(42, ((function() --[[ Line: 355 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v59 = v_u_4.TitleInfoBase:new()
            v59.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 357 ]]
                return "Jolly Holiday Fellow";
            end;
            v59.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 358 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(128, 192, 101);
            end;
            v59.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 359 ]]
                return "Christmas enjoyers!";
            end;
            return v59;
        end)()))
        v_u_16:add_title_for_id(43, ((function() --[[ Line: 362 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v60 = v_u_4.TitleInfoBase:new()
            v60.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 364 ]]
                return "Robeats Fan";
            end;
            v60.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 365 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 255, 255);
            end;
            v60.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 366 ]]
                return "Robeats Fan! Joined the RobeatsDev group on Roblox.";
            end;
            return v60;
        end)()))
        v_u_16:add_title_for_id(44, ((function() --[[ Line: 369 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v61 = v_u_4.TitleInfoBase:new()
            v61.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 371 ]]
                return "Tobu Fan";
            end;
            v61.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 372 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(186, 153, 120);
            end;
            v61.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 373 ]]
                return "Fans of Tobu.";
            end;
            return v61;
        end)()))
        v_u_16:add_title_for_id(45, ((function() --[[ Line: 376 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v62 = v_u_4.TitleInfoBase:new()
            v62.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 378 ]]
                return "Atsuover Fan";
            end;
            v62.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 379 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(207, 147, 110);
            end;
            v62.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 380 ]]
                return "Fans of Atsuover.";
            end;
            return v62;
        end)()))
        v_u_16:add_title_for_id(46, ((function() --[[ Line: 383 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v63 = v_u_4.TitleInfoBase:new()
            v63.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 385 ]]
                return "KepoWorld Fan";
            end;
            v63.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 386 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(233, 164, 223);
            end;
            v63.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 387 ]]
                return "Fans of KepoWorld.";
            end;
            return v63;
        end)()))
        v_u_16:add_title_for_id(47, ((function() --[[ Line: 390 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v64 = v_u_4.TitleInfoBase:new()
            v64.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 392 ]]
                return "Slynk Fan";
            end;
            v64.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 393 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(130, 224, 223);
            end;
            v64.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 394 ]]
                return "Fans of Slynk.";
            end;
            return v64;
        end)()))
        v_u_16:add_title_for_id(48, ((function() --[[ Line: 397 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v65 = v_u_4.TitleInfoBase:new()
            v65.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 399 ]]
                return "Valentine\'s Day Lover";
            end;
            v65.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 400 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(249, 187, 214);
            end;
            v65.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 401 ]]
                return "Lovers of Valentine\'s Day.";
            end;
            return v65;
        end)()))
        v_u_16:add_title_for_id(49, ((function() --[[ Line: 404 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v66 = v_u_4.TitleInfoBase:new()
            v66.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 406 ]]
                return "Similar Outskirts Fan";
            end;
            v66.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 407 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(165, 201, 255);
            end;
            v66.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 408 ]]
                return "Fans of Similar Outskirts.";
            end;
            return v66;
        end)()))
        v_u_16:add_title_for_id(50, ((function() --[[ Line: 411 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v67 = v_u_4.TitleInfoBase:new()
            v67.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 413 ]]
                return "MisoilePunch Fan";
            end;
            v67.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 414 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(153, 255, 235);
            end;
            v67.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 415 ]]
                return "Fans of MisoilePunch.";
            end;
            return v67;
        end)()))
        v_u_16:add_title_for_id(51, ((function() --[[ Line: 418 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v68 = v_u_4.TitleInfoBase:new()
            v68.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 420 ]]
                return "Waterflame Fan";
            end;
            v68.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 421 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 220, 152);
            end;
            v68.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 422 ]]
                return "Fans of Waterflame.";
            end;
            return v68;
        end)()))
        v_u_16:add_title_for_id(52, ((function() --[[ Line: 425 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v69 = v_u_4.TitleInfoBase:new()
            v69.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 427 ]]
                return "LeaF Fan";
            end;
            v69.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 428 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(222, 184, 202);
            end;
            v69.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 429 ]]
                return "Fans of LeaF.";
            end;
            return v69;
        end)()))
        v_u_16:add_title_for_id(53, ((function() --[[ Line: 432 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v70 = v_u_4.TitleInfoBase:new()
            v70.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 434 ]]
                return "Hyper Potions Fan";
            end;
            v70.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 435 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(87, 230, 221);
            end;
            v70.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 436 ]]
                return "Fans of Hyper Potions.";
            end;
            return v70;
        end)()))
        v_u_16:add_title_for_id(54, ((function() --[[ Line: 439 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v71 = v_u_4.TitleInfoBase:new()
            v71.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 441 ]]
                return "brz1128 Fan";
            end;
            v71.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 442 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(179, 235, 211);
            end;
            v71.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 443 ]]
                return "Fans of brz1128.";
            end;
            return v71;
        end)()))
        v_u_16:add_title_for_id(55, ((function() --[[ Line: 446 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v72 = v_u_4.TitleInfoBase:new()
            v72.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 448 ]]
                return "Kurokotei Fan";
            end;
            v72.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 449 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(197, 157, 131);
            end;
            v72.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 450 ]]
                return "Fans of Kurokotei.";
            end;
            return v72;
        end)()))
        v_u_16:add_title_for_id(56, ((function() --[[ Line: 453 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v73 = v_u_4.TitleInfoBase:new()
            v73.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 455 ]]
                return "Laur Fan";
            end;
            v73.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 456 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 248, 20);
            end;
            v73.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 457 ]]
                return "Fans of Laur.";
            end;
            return v73;
        end)()))
        v_u_16:add_title_for_id(57, ((function() --[[ Line: 460 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v74 = v_u_4.TitleInfoBase:new()
            v74.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 462 ]]
                return "UNDEAD CORPORATION Fan";
            end;
            v74.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 463 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 151, 153);
            end;
            v74.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 464 ]]
                return "Fans of UNDEAD CORPORATION.";
            end;
            return v74;
        end)()))
        v_u_16:add_title_for_id(58, ((function() --[[ Line: 467 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v75 = v_u_4.TitleInfoBase:new()
            v75.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 469 ]]
                return "RiraN Fan";
            end;
            v75.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 470 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(236, 193, 83);
            end;
            v75.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 471 ]]
                return "Fans of RiraN.";
            end;
            return v75;
        end)()))
        v_u_16:add_title_for_id(59, ((function() --[[ Line: 474 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v76 = v_u_4.TitleInfoBase:new()
            v76.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 476 ]]
                return "Geoxor Fan";
            end;
            v76.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 477 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(232, 171, 201);
            end;
            v76.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 478 ]]
                return "Fans of Geoxor.";
            end;
            return v76;
        end)()))
        v_u_16:add_title_for_id(60, ((function() --[[ Line: 481 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v77 = v_u_4.TitleInfoBase:new()
            v77.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 483 ]]
                return "Maliboux Fan";
            end;
            v77.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 484 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(216, 167, 115);
            end;
            v77.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 485 ]]
                return "Fans of Maliboux.";
            end;
            return v77;
        end)()))
        v_u_16:add_title_for_id(61, ((function() --[[ Line: 488 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v78 = v_u_4.TitleInfoBase:new()
            v78.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 490 ]]
                return "Summertime Lover";
            end;
            v78.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 491 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(255, 175, 186);
            end;
            v78.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 492 ]]
                return "Summer Carnival lovers.";
            end;
            return v78;
        end)()))
        v_u_16:add_title_for_id(62, ((function() --[[ Line: 495 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v79 = v_u_4.TitleInfoBase:new()
            v79.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 497 ]]
                return "Monstercat Supporter";
            end;
            v79.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 498 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(133, 117, 255);
            end;
            v79.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 499 ]]
                return "Supporters of the Monstercat label.";
            end;
            return v79;
        end)()))
        v_u_16:add_title_for_id(63, ((function() --[[ Line: 502 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v80 = v_u_4.TitleInfoBase:new()
            v80.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 504 ]]
                return "Team Grimoire Fan";
            end;
            v80.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 505 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(240, 136, 180);
            end;
            v80.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 506 ]]
                return "Fans of Team Grimoire.";
            end;
            return v80;
        end)()))
        v_u_16:add_title_for_id(64, ((function() --[[ Line: 509 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v81 = v_u_4.TitleInfoBase:new()
            v81.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 511 ]]
                return "Rutra Fan";
            end;
            v81.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 512 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(233, 110, 114);
            end;
            v81.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 513 ]]
                return "Fans of Rutra.";
            end;
            return v81;
        end)()))
        v_u_16:add_title_for_id(65, ((function() --[[ Line: 516 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v82 = v_u_4.TitleInfoBase:new()
            v82.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 518 ]]
                return "Reku Mochizuki Fan";
            end;
            v82.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 519 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(150, 209, 196);
            end;
            v82.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 520 ]]
                return "Fans of Reku Mochizuki.";
            end;
            return v82;
        end)()))
        v_u_16:add_title_for_id(66, ((function() --[[ Line: 523 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v83 = v_u_4.TitleInfoBase:new()
            v83.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 525 ]]
                return "Ardolf Fan";
            end;
            v83.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 526 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(238, 172, 160);
            end;
            v83.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 527 ]]
                return "Fans of Ardolf.";
            end;
            return v83;
        end)()))
        v_u_16:add_title_for_id(67, ((function() --[[ Line: 530 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v84 = v_u_4.TitleInfoBase:new()
            v84.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 532 ]]
                return "seatrus Fan";
            end;
            v84.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 533 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(218, 121, 215);
            end;
            v84.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 534 ]]
                return "Fans of seatrus.";
            end;
            return v84;
        end)()))
        v_u_16:add_title_for_id(68, ((function() --[[ Line: 537 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v85 = v_u_4.TitleInfoBase:new()
            v85.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 539 ]]
                return "tv room Fan";
            end;
            v85.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 540 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(242, 242, 28);
            end;
            v85.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 541 ]]
                return "Fans of tv room.";
            end;
            return v85;
        end)()))
        v_u_16:add_title_for_id(69, ((function() --[[ Line: 544 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v86 = v_u_4.TitleInfoBase:new()
            v86.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 546 ]]
                return "Japanese School Girl";
            end;
            v86.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 547 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(182, 195, 242);
            end;
            v86.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 548 ]]
                return "Anime main character, member of many after-school clubs.";
            end;
            return v86;
        end)()))
        v_u_16:add_title_for_id(70, ((function() --[[ Line: 551 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v87 = v_u_4.TitleInfoBase:new()
            v87.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 553 ]]
                return "Kobaryo Fan";
            end;
            v87.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 554 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(141, 214, 225);
            end;
            v87.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 555 ]]
                return "Fans of Kobaryo.";
            end;
            return v87;
        end)()))
        v_u_16:add_title_for_id(71, ((function() --[[ Line: 558 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v88 = v_u_4.TitleInfoBase:new()
            v88.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 560 ]]
                return "Cake Maker Extraordinaire";
            end;
            v88.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 561 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(193, 255, 227);
            end;
            v88.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 562 ]]
                return "Fans of Make a Cake.";
            end;
            return v88;
        end)()))
        v_u_16:add_title_for_id(72, ((function() --[[ Line: 565 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v89 = v_u_4.TitleInfoBase:new()
            v89.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 567 ]]
                return "I Played RoBeats in 2022!";
            end;
            v89.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 568 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(249, 179, 1);
            end;
            v89.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 569 ]]
                return "You played RoBeats on New Years in 2022.";
            end;
            return v89;
        end)()))
        v_u_16:add_title_for_id(73, ((function() --[[ Line: 572 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v90 = v_u_4.TitleInfoBase:new()
            v90.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 574 ]]
                return "Sound Space Supporter";
            end;
            v90.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 575 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(61, 218, 249);
            end;
            v90.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 576 ]]
                return "Supporters of Sound Space.";
            end;
            return v90;
        end)()))
        v_u_16:add_title_for_id(74, ((function() --[[ Line: 579 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v91 = v_u_4.TitleInfoBase:new()
            v91.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 581 ]]
                return "t+pazolite Fan";
            end;
            v91.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 582 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(180, 217, 153);
            end;
            v91.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 583 ]]
                return "Fans of t+pazolite.";
            end;
            return v91;
        end)()))
        v_u_16:add_title_for_id(75, ((function() --[[ Line: 586 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v92 = v_u_4.TitleInfoBase:new()
            v92.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 588 ]]
                return "RoBeats 6th Anniversary";
            end;
            v92.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 589 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(241, 136, 138);
            end;
            v92.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 590 ]]
                return "Obtained during the RoBeats 6th Anniversary event.";
            end;
            return v92;
        end)()))
        v_u_16:add_title_for_id(76, ((function() --[[ Line: 593 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v93 = v_u_4.TitleInfoBase:new()
            v93.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 595 ]]
                return "Collect ALL the GEAR!";
            end;
            v93.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 596 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:color3(157, 255, 0);
            end;
            v93.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 597 ]]
                return "Obtained by upgrading to the maximum number of maximum owned gear.";
            end;
            return v93;
        end)()))
        local function _(p94, p_u_95, p_u_96, p_u_97) --[[ Name: create_title ]] --[[ Line: 601 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_4 ]]
            v_u_16:add_title_for_id(p94, ((function() --[[ Line: 602 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_95, (copy 3): p_u_96, (copy 4): p_u_97 ]]
                local v98 = v_u_4.TitleInfoBase:new()
                v98.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                    --[[ Upvalues: (ref 1): p_u_95 ]]
                    return p_u_95;
                end;
                v98.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                    --[[ Upvalues: (ref 1): p_u_96 ]]
                    return p_u_96;
                end;
                v98.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                    --[[ Upvalues: (ref 1): p_u_97 ]]
                    return p_u_97;
                end;
                return v98;
            end)()))
        end;
        local v_u_99 = v_u_2:color3(255, 255, 255)
        local v_u_100 = "See You At The Top!"
        local v_u_101 = "Obtained by completing the first jump challenge. See you at the top!"
        v_u_16:add_title_for_id(77, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_100, (copy 3): v_u_99, (copy 4): v_u_101 ]]
            local v102 = v_u_4.TitleInfoBase:new()
            v102.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_100 ]]
                return v_u_100;
            end;
            v102.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_99 ]]
                return v_u_99;
            end;
            v102.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_101 ]]
                return v_u_101;
            end;
            return v102;
        end)()))
        local v_u_103 = Color3.fromRGB(255, 255, 255)
        local v_u_104 = "My First Collection"
        local v_u_105 = "Obtained by reaching 100 or more collection points."
        v_u_16:add_title_for_id(78, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_104, (copy 3): v_u_103, (copy 4): v_u_105 ]]
            local v106 = v_u_4.TitleInfoBase:new()
            v106.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_104 ]]
                return v_u_104;
            end;
            v106.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_103 ]]
                return v_u_103;
            end;
            v106.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_105 ]]
                return v_u_105;
            end;
            return v106;
        end)()))
        local v_u_107 = Color3.fromRGB(186, 233, 194)
        local v_u_108 = "Beginning Collector"
        local v_u_109 = "Obtained by reaching 500 or more collection points."
        v_u_16:add_title_for_id(79, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_108, (copy 3): v_u_107, (copy 4): v_u_109 ]]
            local v110 = v_u_4.TitleInfoBase:new()
            v110.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_108 ]]
                return v_u_108;
            end;
            v110.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_107 ]]
                return v_u_107;
            end;
            v110.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_109 ]]
                return v_u_109;
            end;
            return v110;
        end)()))
        local v_u_111 = Color3.fromRGB(164, 229, 175)
        local v_u_112 = "I\'ve Collected a Few Things..."
        local v_u_113 = "Obtained by reaching 1000 or more collection points."
        v_u_16:add_title_for_id(80, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_112, (copy 3): v_u_111, (copy 4): v_u_113 ]]
            local v114 = v_u_4.TitleInfoBase:new()
            v114.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_112 ]]
                return v_u_112;
            end;
            v114.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_111 ]]
                return v_u_111;
            end;
            v114.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_113 ]]
                return v_u_113;
            end;
            return v114;
        end)()))
        local v_u_115 = Color3.fromRGB(114, 206, 129)
        local v_u_116 = "Now We\'re Collecting!"
        local v_u_117 = "Obtained by reaching 2000 or more collection points."
        v_u_16:add_title_for_id(81, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_116, (copy 3): v_u_115, (copy 4): v_u_117 ]]
            local v118 = v_u_4.TitleInfoBase:new()
            v118.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_116 ]]
                return v_u_116;
            end;
            v118.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_115 ]]
                return v_u_115;
            end;
            v118.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_117 ]]
                return v_u_117;
            end;
            return v118;
        end)()))
        local v_u_119 = Color3.fromRGB(91, 205, 110)
        local v_u_120 = "Gotta Collect Them All!"
        local v_u_121 = "Obtained by reaching 3000 or more collection points."
        v_u_16:add_title_for_id(82, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_120, (copy 3): v_u_119, (copy 4): v_u_121 ]]
            local v122 = v_u_4.TitleInfoBase:new()
            v122.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_120 ]]
                return v_u_120;
            end;
            v122.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_119 ]]
                return v_u_119;
            end;
            v122.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_121 ]]
                return v_u_121;
            end;
            return v122;
        end)()))
        local v_u_123 = Color3.fromRGB(61, 201, 85)
        local v_u_124 = "Collect All The STUFF!"
        local v_u_125 = "Obtained by reaching 4000 or more collection points."
        v_u_16:add_title_for_id(83, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_124, (copy 3): v_u_123, (copy 4): v_u_125 ]]
            local v126 = v_u_4.TitleInfoBase:new()
            v126.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_124 ]]
                return v_u_124;
            end;
            v126.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_123 ]]
                return v_u_123;
            end;
            v126.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_125 ]]
                return v_u_125;
            end;
            return v126;
        end)()))
        local v_u_127 = Color3.fromRGB(31, 205, 60)
        local v_u_128 = "I\'ve Pretty Much Collected Everything..."
        local v_u_129 = "Obtained by reaching 5000 or more collection points."
        v_u_16:add_title_for_id(84, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_128, (copy 3): v_u_127, (copy 4): v_u_129 ]]
            local v130 = v_u_4.TitleInfoBase:new()
            v130.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_128 ]]
                return v_u_128;
            end;
            v130.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_127 ]]
                return v_u_127;
            end;
            v130.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_129 ]]
                return v_u_129;
            end;
            return v130;
        end)()))
        local v_u_131 = Color3.fromRGB(4, 222, 41)
        local v_u_132 = "Collecting Is My Life!"
        local v_u_133 = "Obtained by reaching 6000 or more collection points."
        v_u_16:add_title_for_id(85, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_132, (copy 3): v_u_131, (copy 4): v_u_133 ]]
            local v134 = v_u_4.TitleInfoBase:new()
            v134.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_132 ]]
                return v_u_132;
            end;
            v134.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_131 ]]
                return v_u_131;
            end;
            v134.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_133 ]]
                return v_u_133;
            end;
            return v134;
        end)()))
        local v_u_135 = Color3.fromRGB(255, 171, 177)
        local v_u_136 = "Spring Sweethearts"
        local v_u_137 = "Obtained during the Spring Festival event."
        v_u_16:add_title_for_id(86, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_136, (copy 3): v_u_135, (copy 4): v_u_137 ]]
            local v138 = v_u_4.TitleInfoBase:new()
            v138.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_136 ]]
                return v_u_136;
            end;
            v138.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_135 ]]
                return v_u_135;
            end;
            v138.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_137 ]]
                return v_u_137;
            end;
            return v138;
        end)()))
        local v_u_139 = Color3.fromRGB(7, 254, 48)
        local v_u_140 = "Consider my Colossal Collection!"
        local v_u_141 = "Obtained by reaching 7000 or more collection points."
        v_u_16:add_title_for_id(87, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_140, (copy 3): v_u_139, (copy 4): v_u_141 ]]
            local v142 = v_u_4.TitleInfoBase:new()
            v142.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_140 ]]
                return v_u_140;
            end;
            v142.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_139 ]]
                return v_u_139;
            end;
            v142.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_141 ]]
                return v_u_141;
            end;
            return v142;
        end)()))
        local v_u_143 = Color3.fromRGB(128, 213, 206)
        local v_u_144 = "Chiptune Connoisseur"
        local v_u_145 = "Obtained from the \'Celebration of Chiptunes\' event."
        v_u_16:add_title_for_id(88, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_144, (copy 3): v_u_143, (copy 4): v_u_145 ]]
            local v146 = v_u_4.TitleInfoBase:new()
            v146.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_144 ]]
                return v_u_144;
            end;
            v146.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_143 ]]
                return v_u_143;
            end;
            v146.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_145 ]]
                return v_u_145;
            end;
            return v146;
        end)()))
        local v_u_147 = Color3.fromRGB(162, 191, 238)
        local v_u_148 = "HyuN Fan"
        local v_u_149 = "Fans of HyuN."
        v_u_16:add_title_for_id(89, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_148, (copy 3): v_u_147, (copy 4): v_u_149 ]]
            local v150 = v_u_4.TitleInfoBase:new()
            v150.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_148 ]]
                return v_u_148;
            end;
            v150.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_147 ]]
                return v_u_147;
            end;
            v150.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_149 ]]
                return v_u_149;
            end;
            return v150;
        end)()))
        local v_u_151 = Color3.fromRGB(253, 193, 212)
        local v_u_152 = "Kanro Fan"
        local v_u_153 = "Fans of Kanro."
        v_u_16:add_title_for_id(90, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_152, (copy 3): v_u_151, (copy 4): v_u_153 ]]
            local v154 = v_u_4.TitleInfoBase:new()
            v154.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_152 ]]
                return v_u_152;
            end;
            v154.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_151 ]]
                return v_u_151;
            end;
            v154.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_153 ]]
                return v_u_153;
            end;
            return v154;
        end)()))
        local v_u_155 = Color3.fromRGB(211, 223, 80)
        local v_u_156 = "Stranded on a Deserted Island..."
        local v_u_157 = "Obtained from the \'Sweltering Summer Spectacle!\' event."
        v_u_16:add_title_for_id(91, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_156, (copy 3): v_u_155, (copy 4): v_u_157 ]]
            local v158 = v_u_4.TitleInfoBase:new()
            v158.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_156 ]]
                return v_u_156;
            end;
            v158.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_155 ]]
                return v_u_155;
            end;
            v158.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_157 ]]
                return v_u_157;
            end;
            return v158;
        end)()))
        local v_u_159 = Color3.fromRGB(246, 226, 154)
        local v_u_160 = "Beach-Combing Treasure Hunter!"
        local v_u_161 = "Obtained from collecting all 8 hidden stars in the summer lobby."
        v_u_16:add_title_for_id(92, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_160, (copy 3): v_u_159, (copy 4): v_u_161 ]]
            local v162 = v_u_4.TitleInfoBase:new()
            v162.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_160 ]]
                return v_u_160;
            end;
            v162.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_159 ]]
                return v_u_159;
            end;
            v162.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_161 ]]
                return v_u_161;
            end;
            return v162;
        end)()))
        local v_u_163 = Color3.fromRGB(191, 198, 241)
        local v_u_164 = "Synthion Fan"
        local v_u_165 = "Fans of Synthion."
        v_u_16:add_title_for_id(93, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_164, (copy 3): v_u_163, (copy 4): v_u_165 ]]
            local v166 = v_u_4.TitleInfoBase:new()
            v166.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_164 ]]
                return v_u_164;
            end;
            v166.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_163 ]]
                return v_u_163;
            end;
            v166.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_165 ]]
                return v_u_165;
            end;
            return v166;
        end)()))
        local v_u_167 = Color3.fromRGB(253, 205, 218)
        local v_u_168 = "Toiling on Tasks"
        local v_u_169 = "Obtained by placing top 200 in the \'Total Score\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(94, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_168, (copy 3): v_u_167, (copy 4): v_u_169 ]]
            local v170 = v_u_4.TitleInfoBase:new()
            v170.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_168 ]]
                return v_u_168;
            end;
            v170.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_167 ]]
                return v_u_167;
            end;
            v170.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_169 ]]
                return v_u_169;
            end;
            return v170;
        end)()))
        local v_u_171 = Color3.fromRGB(249, 167, 189)
        local v_u_172 = "Chore Colleague"
        local v_u_173 = "Obtained by placing top 100 in the \'Total Score\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(95, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_172, (copy 3): v_u_171, (copy 4): v_u_173 ]]
            local v174 = v_u_4.TitleInfoBase:new()
            v174.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_172 ]]
                return v_u_172;
            end;
            v174.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_171 ]]
                return v_u_171;
            end;
            v174.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_173 ]]
                return v_u_173;
            end;
            return v174;
        end)()))
        local v_u_175 = Color3.fromRGB(249, 119, 153)
        local v_u_176 = "Assignment Associate"
        local v_u_177 = "Obtained by placing top 25 in the \'Total Score\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(96, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_176, (copy 3): v_u_175, (copy 4): v_u_177 ]]
            local v178 = v_u_4.TitleInfoBase:new()
            v178.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_176 ]]
                return v_u_176;
            end;
            v178.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_175 ]]
                return v_u_175;
            end;
            v178.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_177 ]]
                return v_u_177;
            end;
            return v178;
        end)()))
        local v_u_179 = Color3.fromRGB(254, 70, 119)
        local v_u_180 = "Weekly Warrior"
        local v_u_181 = "Obtained by placing top 5 in the \'Total Score\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(97, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_180, (copy 3): v_u_179, (copy 4): v_u_181 ]]
            local v182 = v_u_4.TitleInfoBase:new()
            v182.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_180 ]]
                return v_u_180;
            end;
            v182.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_179 ]]
                return v_u_179;
            end;
            v182.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_181 ]]
                return v_u_181;
            end;
            return v182;
        end)()))
        local v_u_183 = Color3.fromRGB(255, 9, 75)
        local v_u_184 = "Mission Mastermind"
        local v_u_185 = "Obtained by placing 1st in the \'Total Score\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(98, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_184, (copy 3): v_u_183, (copy 4): v_u_185 ]]
            local v186 = v_u_4.TitleInfoBase:new()
            v186.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_184 ]]
                return v_u_184;
            end;
            v186.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_183 ]]
                return v_u_183;
            end;
            v186.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_185 ]]
                return v_u_185;
            end;
            return v186;
        end)()))
        local v_u_187 = Color3.fromRGB(112, 190, 250)
        local v_u_188 = "EmoCosine Fan"
        local v_u_189 = "Fans of EmoCosine."
        v_u_16:add_title_for_id(99, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_188, (copy 3): v_u_187, (copy 4): v_u_189 ]]
            local v190 = v_u_4.TitleInfoBase:new()
            v190.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_188 ]]
                return v_u_188;
            end;
            v190.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_187 ]]
                return v_u_187;
            end;
            v190.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_189 ]]
                return v_u_189;
            end;
            return v190;
        end)()))
        local v_u_191 = Color3.fromRGB(176, 207, 222)
        local v_u_192 = "I Like Balloons!"
        local v_u_193 = "Obtained by jumping on some balloons during the \'Summer Carnival\' event."
        v_u_16:add_title_for_id(100, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_192, (copy 3): v_u_191, (copy 4): v_u_193 ]]
            local v194 = v_u_4.TitleInfoBase:new()
            v194.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_192 ]]
                return v_u_192;
            end;
            v194.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_191 ]]
                return v_u_191;
            end;
            v194.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_193 ]]
                return v_u_193;
            end;
            return v194;
        end)()))
        local v_u_195 = Color3.fromRGB(255, 214, 179)
        local v_u_196 = "Shabby Slacker"
        local v_u_197 = "Obtained by placing top 200 in the \'Lowest Gear Power\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(101, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_196, (copy 3): v_u_195, (copy 4): v_u_197 ]]
            local v198 = v_u_4.TitleInfoBase:new()
            v198.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_196 ]]
                return v_u_196;
            end;
            v198.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_195 ]]
                return v_u_195;
            end;
            v198.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_197 ]]
                return v_u_197;
            end;
            return v198;
        end)()))
        local v_u_199 = Color3.fromRGB(255, 204, 153)
        local v_u_200 = "Laid-back Laborer"
        local v_u_201 = "Obtained by placing top 100 in the \'Lowest Gear Power\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(102, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_200, (copy 3): v_u_199, (copy 4): v_u_201 ]]
            local v202 = v_u_4.TitleInfoBase:new()
            v202.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_200 ]]
                return v_u_200;
            end;
            v202.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_199 ]]
                return v_u_199;
            end;
            v202.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_201 ]]
                return v_u_201;
            end;
            return v202;
        end)()))
        local v_u_203 = Color3.fromRGB(255, 177, 105)
        local v_u_204 = "Relaxed Roustabout"
        local v_u_205 = "Obtained by placing top 25 in the \'Lowest Gear Power\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(103, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_204, (copy 3): v_u_203, (copy 4): v_u_205 ]]
            local v206 = v_u_4.TitleInfoBase:new()
            v206.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_204 ]]
                return v_u_204;
            end;
            v206.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_203 ]]
                return v_u_203;
            end;
            v206.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_205 ]]
                return v_u_205;
            end;
            return v206;
        end)()))
        local v_u_207 = Color3.fromRGB(255, 125, 54)
        local v_u_208 = "Carefree Contestant"
        local v_u_209 = "Obtained by placing top 5 in the \'Lowest Gear Power\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(104, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_208, (copy 3): v_u_207, (copy 4): v_u_209 ]]
            local v210 = v_u_4.TitleInfoBase:new()
            v210.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_208 ]]
                return v_u_208;
            end;
            v210.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_207 ]]
                return v_u_207;
            end;
            v210.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_209 ]]
                return v_u_209;
            end;
            return v210;
        end)()))
        local v_u_211 = Color3.fromRGB(255, 90, 0)
        local v_u_212 = "Chief Casual Competitor"
        local v_u_213 = "Obtained by placing 1st in the \'Lowest Gear Power\' category of a weekly mission leaderboard."
        v_u_16:add_title_for_id(105, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_212, (copy 3): v_u_211, (copy 4): v_u_213 ]]
            local v214 = v_u_4.TitleInfoBase:new()
            v214.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_212 ]]
                return v_u_212;
            end;
            v214.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_211 ]]
                return v_u_211;
            end;
            v214.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_213 ]]
                return v_u_213;
            end;
            return v214;
        end)()))
        local v_u_215 = Color3.fromRGB(216, 176, 191)
        local v_u_216 = "Bossfight Fan"
        local v_u_217 = "Fans of Bossfight."
        v_u_16:add_title_for_id(106, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_216, (copy 3): v_u_215, (copy 4): v_u_217 ]]
            local v218 = v_u_4.TitleInfoBase:new()
            v218.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_216 ]]
                return v_u_216;
            end;
            v218.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_215 ]]
                return v_u_215;
            end;
            v218.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_217 ]]
                return v_u_217;
            end;
            return v218;
        end)()))
        local v_u_219 = Color3.fromRGB(145, 223, 188)
        local v_u_220 = "Party Mode - Activate!"
        local v_u_221 = "Obtained by activating party mode (during the event of the same name)."
        v_u_16:add_title_for_id(107, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_220, (copy 3): v_u_219, (copy 4): v_u_221 ]]
            local v222 = v_u_4.TitleInfoBase:new()
            v222.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_220 ]]
                return v_u_220;
            end;
            v222.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_219 ]]
                return v_u_219;
            end;
            v222.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_221 ]]
                return v_u_221;
            end;
            return v222;
        end)()))
        local v_u_223 = Color3.fromRGB(244, 169, 77)
        local v_u_224 = "Autumn Appreciator"
        local v_u_225 = "Obtained during the Autumn Festival event."
        v_u_16:add_title_for_id(108, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_224, (copy 3): v_u_223, (copy 4): v_u_225 ]]
            local v226 = v_u_4.TitleInfoBase:new()
            v226.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_224 ]]
                return v_u_224;
            end;
            v226.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_223 ]]
                return v_u_223;
            end;
            v226.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_225 ]]
                return v_u_225;
            end;
            return v226;
        end)()))
        local v_u_227 = Color3.fromRGB(255, 255, 255)
        local v_u_228 = "PC Enjoyer"
        local v_u_229 = "Obtained by playing on PC."
        v_u_16:add_title_for_id(109, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_228, (copy 3): v_u_227, (copy 4): v_u_229 ]]
            local v230 = v_u_4.TitleInfoBase:new()
            v230.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_228 ]]
                return v_u_228;
            end;
            v230.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_227 ]]
                return v_u_227;
            end;
            v230.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_229 ]]
                return v_u_229;
            end;
            return v230;
        end)()))
        local v_u_231 = Color3.fromRGB(255, 255, 255)
        local v_u_232 = "Mobile Enjoyer"
        local v_u_233 = "Obtained by playing on a mobile device."
        v_u_16:add_title_for_id(110, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_232, (copy 3): v_u_231, (copy 4): v_u_233 ]]
            local v234 = v_u_4.TitleInfoBase:new()
            v234.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_232 ]]
                return v_u_232;
            end;
            v234.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_231 ]]
                return v_u_231;
            end;
            v234.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_233 ]]
                return v_u_233;
            end;
            return v234;
        end)()))
        local v_u_235 = Color3.fromRGB(255, 255, 255)
        local v_u_236 = "Console Enjoyer"
        local v_u_237 = "Obtained by playing on a console."
        v_u_16:add_title_for_id(111, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_236, (copy 3): v_u_235, (copy 4): v_u_237 ]]
            local v238 = v_u_4.TitleInfoBase:new()
            v238.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_236 ]]
                return v_u_236;
            end;
            v238.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_235 ]]
                return v_u_235;
            end;
            v238.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_237 ]]
                return v_u_237;
            end;
            return v238;
        end)()))
        local v_u_239 = Color3.fromRGB(165, 237, 224)
        local v_u_240 = "keisei Fan"
        local v_u_241 = "Fans of keisei."
        v_u_16:add_title_for_id(112, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_240, (copy 3): v_u_239, (copy 4): v_u_241 ]]
            local v242 = v_u_4.TitleInfoBase:new()
            v242.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_240 ]]
                return v_u_240;
            end;
            v242.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_239 ]]
                return v_u_239;
            end;
            v242.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_241 ]]
                return v_u_241;
            end;
            return v242;
        end)()))
        local v_u_243 = Color3.fromRGB(231, 245, 246)
        local v_u_244 = "Loading more Loadouts..."
        local v_u_245 = "Obtained by purchasing 1 extra loadout slot."
        v_u_16:add_title_for_id(113, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_244, (copy 3): v_u_243, (copy 4): v_u_245 ]]
            local v246 = v_u_4.TitleInfoBase:new()
            v246.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_244 ]]
                return v_u_244;
            end;
            v246.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_243 ]]
                return v_u_243;
            end;
            v246.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_245 ]]
                return v_u_245;
            end;
            return v246;
        end)()))
        local v_u_247 = Color3.fromRGB(181, 234, 239)
        local v_u_248 = "Locked and Loaded!"
        local v_u_249 = "Obtained by purchasing 5 extra loadout slots."
        v_u_16:add_title_for_id(114, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_248, (copy 3): v_u_247, (copy 4): v_u_249 ]]
            local v250 = v_u_4.TitleInfoBase:new()
            v250.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_248 ]]
                return v_u_248;
            end;
            v250.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_247 ]]
                return v_u_247;
            end;
            v250.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_249 ]]
                return v_u_249;
            end;
            return v250;
        end)()))
        local v_u_251 = Color3.fromRGB(94, 244, 235)
        local v_u_252 = "Checkout these Loadouts!"
        local v_u_253 = "Obtained by purchasing all 10 extra loadout slots."
        v_u_16:add_title_for_id(115, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_252, (copy 3): v_u_251, (copy 4): v_u_253 ]]
            local v254 = v_u_4.TitleInfoBase:new()
            v254.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_252 ]]
                return v_u_252;
            end;
            v254.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_251 ]]
                return v_u_251;
            end;
            v254.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_253 ]]
                return v_u_253;
            end;
            return v254;
        end)()))
        local v_u_255 = Color3.fromRGB(24, 255, 244)
        local v_u_256 = "Fully Decked-Out and Tricked-Out in Load-Outs!"
        local v_u_257 = "Obtained by purchasing all extra loadout slots and gear inventory slots."
        v_u_16:add_title_for_id(116, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_256, (copy 3): v_u_255, (copy 4): v_u_257 ]]
            local v258 = v_u_4.TitleInfoBase:new()
            v258.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_256 ]]
                return v_u_256;
            end;
            v258.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_255 ]]
                return v_u_255;
            end;
            v258.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_257 ]]
                return v_u_257;
            end;
            return v258;
        end)()))
        local v_u_259 = Color3.fromRGB(36, 255, 160)
        local v_u_260 = "Continent-Crossing Conquerer of Collections"
        local v_u_261 = "Obtained by reaching 8000 or more collection points."
        v_u_16:add_title_for_id(117, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_260, (copy 3): v_u_259, (copy 4): v_u_261 ]]
            local v262 = v_u_4.TitleInfoBase:new()
            v262.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_260 ]]
                return v_u_260;
            end;
            v262.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_259 ]]
                return v_u_259;
            end;
            v262.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_261 ]]
                return v_u_261;
            end;
            return v262;
        end)()))
        local v_u_263 = Color3.fromRGB(36, 255, 208)
        local v_u_264 = "Collector of all Certified Creations of the Cosmos"
        local v_u_265 = "Obtained by reaching 9000 or more collection points."
        v_u_16:add_title_for_id(118, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_264, (copy 3): v_u_263, (copy 4): v_u_265 ]]
            local v266 = v_u_4.TitleInfoBase:new()
            v266.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_264 ]]
                return v_u_264;
            end;
            v266.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_263 ]]
                return v_u_263;
            end;
            v266.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_265 ]]
                return v_u_265;
            end;
            return v266;
        end)()))
        local v_u_267 = Color3.fromRGB(249, 179, 1)
        local v_u_268 = "I Played RoBeats in 2023!"
        local v_u_269 = "You played RoBeats on New Years in 2023."
        v_u_16:add_title_for_id(119, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_268, (copy 3): v_u_267, (copy 4): v_u_269 ]]
            local v270 = v_u_4.TitleInfoBase:new()
            v270.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_268 ]]
                return v_u_268;
            end;
            v270.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_267 ]]
                return v_u_267;
            end;
            v270.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_269 ]]
                return v_u_269;
            end;
            return v270;
        end)()))
        local v_u_271 = Color3.fromRGB(249, 116, 116)
        local v_u_272 = "Juggernaut Fan"
        local v_u_273 = "Fans of Juggernaut."
        v_u_16:add_title_for_id(120, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_272, (copy 3): v_u_271, (copy 4): v_u_273 ]]
            local v274 = v_u_4.TitleInfoBase:new()
            v274.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_272 ]]
                return v_u_272;
            end;
            v274.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_271 ]]
                return v_u_271;
            end;
            v274.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_273 ]]
                return v_u_273;
            end;
            return v274;
        end)()))
        local v_u_275 = Color3.fromRGB(245, 176, 130)
        local v_u_276 = "Challenge Pass Master"
        local v_u_277 = "Given to players who max out the monthly challenge pass."
        v_u_16:add_title_for_id(121, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_276, (copy 3): v_u_275, (copy 4): v_u_277 ]]
            local v278 = v_u_4.TitleInfoBase:new()
            v278.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_276 ]]
                return v_u_276;
            end;
            v278.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_275 ]]
                return v_u_275;
            end;
            v278.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_277 ]]
                return v_u_277;
            end;
            return v278;
        end)()))
        local v_u_279 = Color3.fromRGB(237, 244, 175)
        local v_u_280 = "Halv Fan"
        local v_u_281 = "Fans of Halv."
        v_u_16:add_title_for_id(123, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_280, (copy 3): v_u_279, (copy 4): v_u_281 ]]
            local v282 = v_u_4.TitleInfoBase:new()
            v282.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_280 ]]
                return v_u_280;
            end;
            v282.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_279 ]]
                return v_u_279;
            end;
            v282.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_281 ]]
                return v_u_281;
            end;
            return v282;
        end)()))
        local v_u_283 = Color3.fromRGB(241, 136, 138)
        local v_u_284 = "RoBeats 7th Anniversary"
        local v_u_285 = "Obtained during the RoBeats 7th Anniversary event."
        v_u_16:add_title_for_id(124, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_284, (copy 3): v_u_283, (copy 4): v_u_285 ]]
            local v286 = v_u_4.TitleInfoBase:new()
            v286.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_284 ]]
                return v_u_284;
            end;
            v286.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_283 ]]
                return v_u_283;
            end;
            v286.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_285 ]]
                return v_u_285;
            end;
            return v286;
        end)()))
        local v_u_287 = Color3.fromRGB(147, 219, 237)
        local v_u_288 = "you Fan"
        local v_u_289 = "Fans of you."
        v_u_16:add_title_for_id(125, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_288, (copy 3): v_u_287, (copy 4): v_u_289 ]]
            local v290 = v_u_4.TitleInfoBase:new()
            v290.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_288 ]]
                return v_u_288;
            end;
            v290.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_287 ]]
                return v_u_287;
            end;
            v290.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_289 ]]
                return v_u_289;
            end;
            return v290;
        end)()))
        local v_u_291 = Color3.fromRGB(246, 172, 163)
        local v_u_292 = "Apocalypse Survivor"
        local v_u_293 = "Survived the apocalypse!"
        v_u_16:add_title_for_id(126, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_292, (copy 3): v_u_291, (copy 4): v_u_293 ]]
            local v294 = v_u_4.TitleInfoBase:new()
            v294.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_292 ]]
                return v_u_292;
            end;
            v294.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_291 ]]
                return v_u_291;
            end;
            v294.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_293 ]]
                return v_u_293;
            end;
            return v294;
        end)()))
        local v_u_295 = Color3.fromRGB(96, 207, 247)
        local v_u_296 = "Project Skylate Fan"
        local v_u_297 = "Fans of Project Skylate."
        v_u_16:add_title_for_id(127, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_296, (copy 3): v_u_295, (copy 4): v_u_297 ]]
            local v298 = v_u_4.TitleInfoBase:new()
            v298.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_296 ]]
                return v_u_296;
            end;
            v298.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_295 ]]
                return v_u_295;
            end;
            v298.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_297 ]]
                return v_u_297;
            end;
            return v298;
        end)()))
        local v_u_299 = Color3.fromRGB(90, 231, 184)
        local v_u_300 = "AAAA Fan"
        local v_u_301 = "Fans of AAAA."
        v_u_16:add_title_for_id(128, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_300, (copy 3): v_u_299, (copy 4): v_u_301 ]]
            local v302 = v_u_4.TitleInfoBase:new()
            v302.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_300 ]]
                return v_u_300;
            end;
            v302.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_299 ]]
                return v_u_299;
            end;
            v302.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_301 ]]
                return v_u_301;
            end;
            return v302;
        end)()))
        local v_u_303 = Color3.fromRGB(192, 234, 238)
        local v_u_304 = "No-Miss Amateur!"
        local v_u_305 = "Obtained by completing a No-Miss mission of Amateur rank."
        v_u_16:add_title_for_id(129, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_304, (copy 3): v_u_303, (copy 4): v_u_305 ]]
            local v306 = v_u_4.TitleInfoBase:new()
            v306.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_304 ]]
                return v_u_304;
            end;
            v306.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_303 ]]
                return v_u_303;
            end;
            v306.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_305 ]]
                return v_u_305;
            end;
            return v306;
        end)()))
        local v_u_307 = Color3.fromRGB(125, 196, 241)
        local v_u_308 = "No-Miss Pro!"
        local v_u_309 = "Obtained by completing a No-Miss mission of Pro rank."
        v_u_16:add_title_for_id(130, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_308, (copy 3): v_u_307, (copy 4): v_u_309 ]]
            local v310 = v_u_4.TitleInfoBase:new()
            v310.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_308 ]]
                return v_u_308;
            end;
            v310.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_307 ]]
                return v_u_307;
            end;
            v310.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_309 ]]
                return v_u_309;
            end;
            return v310;
        end)()))
        local v_u_311 = Color3.fromRGB(38, 168, 244)
        local v_u_312 = "No-Miss Star!"
        local v_u_313 = "Obtained by completing a No-Miss mission of Star rank."
        v_u_16:add_title_for_id(131, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_312, (copy 3): v_u_311, (copy 4): v_u_313 ]]
            local v314 = v_u_4.TitleInfoBase:new()
            v314.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_312 ]]
                return v_u_312;
            end;
            v314.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_311 ]]
                return v_u_311;
            end;
            v314.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_313 ]]
                return v_u_313;
            end;
            return v314;
        end)()))
        local v_u_315 = Color3.fromRGB(255, 201, 82)
        local v_u_316 = "Kagetora Fan"
        local v_u_317 = "Fans of Kagetora."
        v_u_16:add_title_for_id(132, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_316, (copy 3): v_u_315, (copy 4): v_u_317 ]]
            local v318 = v_u_4.TitleInfoBase:new()
            v318.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_316 ]]
                return v_u_316;
            end;
            v318.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_315 ]]
                return v_u_315;
            end;
            v318.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_317 ]]
                return v_u_317;
            end;
            return v318;
        end)()))
        local v_u_319 = Color3.fromRGB(200, 220, 200)
        local v_u_320 = "I\'m just here for The Games!"
        local v_u_321 = "Completed a quest from the Roblox \'The Games\' event!"
        v_u_16:add_title_for_id(133, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_320, (copy 3): v_u_319, (copy 4): v_u_321 ]]
            local v322 = v_u_4.TitleInfoBase:new()
            v322.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_320 ]]
                return v_u_320;
            end;
            v322.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_319 ]]
                return v_u_319;
            end;
            v322.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_321 ]]
                return v_u_321;
            end;
            return v322;
        end)()))
        local v_u_323 = Color3.fromRGB(242, 104, 104)
        local v_u_324 = "USAO Fan"
        local v_u_325 = "Fans of USAO."
        v_u_16:add_title_for_id(134, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_324, (copy 3): v_u_323, (copy 4): v_u_325 ]]
            local v326 = v_u_4.TitleInfoBase:new()
            v326.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_324 ]]
                return v_u_324;
            end;
            v326.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_323 ]]
                return v_u_323;
            end;
            v326.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_325 ]]
                return v_u_325;
            end;
            return v326;
        end)()))
        local v_u_327 = Color3.fromRGB(105, 217, 208)
        local v_u_328 = "nanobii Fan"
        local v_u_329 = "Fans of nanobii."
        v_u_16:add_title_for_id(135, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_328, (copy 3): v_u_327, (copy 4): v_u_329 ]]
            local v330 = v_u_4.TitleInfoBase:new()
            v330.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_328 ]]
                return v_u_328;
            end;
            v330.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_327 ]]
                return v_u_327;
            end;
            v330.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_329 ]]
                return v_u_329;
            end;
            return v330;
        end)()))
        local v_u_331 = Color3.fromRGB(235, 100, 42)
        local v_u_332 = "Adept of this Autumnal Abode"
        local v_u_333 = "Obtained by finding all the hidden leaves in the Autumn lobby."
        v_u_16:add_title_for_id(136, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_332, (copy 3): v_u_331, (copy 4): v_u_333 ]]
            local v334 = v_u_4.TitleInfoBase:new()
            v334.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_332 ]]
                return v_u_332;
            end;
            v334.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_331 ]]
                return v_u_331;
            end;
            v334.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_333 ]]
                return v_u_333;
            end;
            return v334;
        end)()))
        local v_u_335 = Color3.fromRGB(255, 242, 54)
        local v_u_336 = "Black17 Believer"
        local v_u_337 = "Fans of Black17."
        v_u_16:add_title_for_id(137, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_336, (copy 3): v_u_335, (copy 4): v_u_337 ]]
            local v338 = v_u_4.TitleInfoBase:new()
            v338.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_336 ]]
                return v_u_336;
            end;
            v338.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_335 ]]
                return v_u_335;
            end;
            v338.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_337 ]]
                return v_u_337;
            end;
            return v338;
        end)()))
        local v_u_339 = Color3.fromRGB(253, 225, 147)
        local v_u_340 = "YooH Fan"
        local v_u_341 = "Fans of YooH."
        v_u_16:add_title_for_id(138, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_340, (copy 3): v_u_339, (copy 4): v_u_341 ]]
            local v342 = v_u_4.TitleInfoBase:new()
            v342.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_340 ]]
                return v_u_340;
            end;
            v342.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_339 ]]
                return v_u_339;
            end;
            v342.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_341 ]]
                return v_u_341;
            end;
            return v342;
        end)()))
        local v_u_343 = Color3.fromRGB(249, 179, 1)
        local v_u_344 = "I Played RoBeats in 2024!"
        local v_u_345 = "You played RoBeats on New Years in 2024."
        v_u_16:add_title_for_id(139, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_344, (copy 3): v_u_343, (copy 4): v_u_345 ]]
            local v346 = v_u_4.TitleInfoBase:new()
            v346.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_344 ]]
                return v_u_344;
            end;
            v346.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_343 ]]
                return v_u_343;
            end;
            v346.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_345 ]]
                return v_u_345;
            end;
            return v346;
        end)()))
        local v_u_347 = Color3.fromRGB(218, 188, 229)
        local v_u_348 = "Snail\'s House Fan"
        local v_u_349 = "Fans of Snail\'s House."
        v_u_16:add_title_for_id(140, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_348, (copy 3): v_u_347, (copy 4): v_u_349 ]]
            local v350 = v_u_4.TitleInfoBase:new()
            v350.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_348 ]]
                return v_u_348;
            end;
            v350.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_347 ]]
                return v_u_347;
            end;
            v350.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_349 ]]
                return v_u_349;
            end;
            return v350;
        end)()))
        local v_u_351 = Color3.fromRGB(230, 154, 154)
        local v_u_352 = "Heavy Metal Fan"
        local v_u_353 = "Fans of Heavy Metal."
        v_u_16:add_title_for_id(141, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_352, (copy 3): v_u_351, (copy 4): v_u_353 ]]
            local v354 = v_u_4.TitleInfoBase:new()
            v354.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_352 ]]
                return v_u_352;
            end;
            v354.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_351 ]]
                return v_u_351;
            end;
            v354.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_353 ]]
                return v_u_353;
            end;
            return v354;
        end)()))
        local v_u_355 = Color3.fromRGB(253, 196, 208)
        local v_u_356 = "Fusq Fan"
        local v_u_357 = "Fans of Fusq."
        v_u_16:add_title_for_id(142, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_356, (copy 3): v_u_355, (copy 4): v_u_357 ]]
            local v358 = v_u_4.TitleInfoBase:new()
            v358.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_356 ]]
                return v_u_356;
            end;
            v358.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_355 ]]
                return v_u_355;
            end;
            v358.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_357 ]]
                return v_u_357;
            end;
            return v358;
        end)()))
        local v_u_359 = Color3.fromRGB(242, 173, 12)
        local v_u_360 = "RoBeats 8th Anniversary"
        local v_u_361 = "Obtained during the RoBeats 8th Anniversary event."
        v_u_16:add_title_for_id(143, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_360, (copy 3): v_u_359, (copy 4): v_u_361 ]]
            local v362 = v_u_4.TitleInfoBase:new()
            v362.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_360 ]]
                return v_u_360;
            end;
            v362.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_359 ]]
                return v_u_359;
            end;
            v362.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_361 ]]
                return v_u_361;
            end;
            return v362;
        end)()))
        local v_u_363 = Color3.fromRGB(255, 255, 255)
        local v_u_364 = "I Like RoBeats!"
        local v_u_365 = "You liked RoBeats. Like & Subscribe!"
        v_u_16:add_title_for_id(144, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_364, (copy 3): v_u_363, (copy 4): v_u_365 ]]
            local v366 = v_u_4.TitleInfoBase:new()
            v366.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_364 ]]
                return v_u_364;
            end;
            v366.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_363 ]]
                return v_u_363;
            end;
            v366.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_365 ]]
                return v_u_365;
            end;
            return v366;
        end)()))
        local v_u_367 = Color3.fromRGB(238, 128, 169)
        local v_u_368 = "Lappy Fan"
        local v_u_369 = "Fans of Lappy."
        v_u_16:add_title_for_id(145, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_368, (copy 3): v_u_367, (copy 4): v_u_369 ]]
            local v370 = v_u_4.TitleInfoBase:new()
            v370.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_368 ]]
                return v_u_368;
            end;
            v370.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_367 ]]
                return v_u_367;
            end;
            v370.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_369 ]]
                return v_u_369;
            end;
            return v370;
        end)()))
        local v_u_371 = Color3.fromRGB(141, 242, 242)
        local v_u_372 = "Trance Trailblazer"
        local v_u_373 = "Fans of Trance. Let\'s trailblaze into the night!"
        v_u_16:add_title_for_id(146, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_372, (copy 3): v_u_371, (copy 4): v_u_373 ]]
            local v374 = v_u_4.TitleInfoBase:new()
            v374.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_372 ]]
                return v_u_372;
            end;
            v374.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_371 ]]
                return v_u_371;
            end;
            v374.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_373 ]]
                return v_u_373;
            end;
            return v374;
        end)()))
        local v_u_375 = Color3.fromRGB(255, 220, 152)
        local v_u_376 = "Electroman Returns!"
        local v_u_377 = "You gained the ability to control the electricity from within. Electro-man!"
        v_u_16:add_title_for_id(147, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_376, (copy 3): v_u_375, (copy 4): v_u_377 ]]
            local v378 = v_u_4.TitleInfoBase:new()
            v378.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_376 ]]
                return v_u_376;
            end;
            v378.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_375 ]]
                return v_u_375;
            end;
            v378.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_377 ]]
                return v_u_377;
            end;
            return v378;
        end)()))
        local v_u_379 = Color3.fromRGB(152, 235, 233)
        local v_u_380 = "Grand Gatherer of Glorious Galactic Gains"
        local v_u_381 = "Obtained by reaching 10,000 or more collection points."
        v_u_16:add_title_for_id(148, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_380, (copy 3): v_u_379, (copy 4): v_u_381 ]]
            local v382 = v_u_4.TitleInfoBase:new()
            v382.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_380 ]]
                return v_u_380;
            end;
            v382.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_379 ]]
                return v_u_379;
            end;
            v382.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_381 ]]
                return v_u_381;
            end;
            return v382;
        end)()))
        local v_u_383 = Color3.fromRGB(160, 250, 245)
        local v_u_384 = "Infinite Investor of Indescribable Inventories"
        local v_u_385 = "Obtained by reaching 11,000 or more collection points."
        v_u_16:add_title_for_id(149, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_384, (copy 3): v_u_383, (copy 4): v_u_385 ]]
            local v386 = v_u_4.TitleInfoBase:new()
            v386.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_384 ]]
                return v_u_384;
            end;
            v386.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_383 ]]
                return v_u_383;
            end;
            v386.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_385 ]]
                return v_u_385;
            end;
            return v386;
        end)()))
        local v_u_387 = Color3.fromRGB(223, 182, 69)
        local v_u_388 = "BlackY Fan"
        local v_u_389 = "Fans of BlackY."
        v_u_16:add_title_for_id(150, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_388, (copy 3): v_u_387, (copy 4): v_u_389 ]]
            local v390 = v_u_4.TitleInfoBase:new()
            v390.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_388 ]]
                return v_u_388;
            end;
            v390.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_387 ]]
                return v_u_387;
            end;
            v390.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_389 ]]
                return v_u_389;
            end;
            return v390;
        end)()))
        local v_u_391 = Color3.fromRGB(231, 237, 40)
        local v_u_392 = "Kagi Fan"
        local v_u_393 = "Fans of Kagi."
        v_u_16:add_title_for_id(151, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_392, (copy 3): v_u_391, (copy 4): v_u_393 ]]
            local v394 = v_u_4.TitleInfoBase:new()
            v394.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): v_u_392 ]]
                return v_u_392;
            end;
            v394.get_color = function(_) --[[ Name: get_color ]] --[[ Line: 605 ]]
                --[[ Upvalues: (ref 1): v_u_391 ]]
                return v_u_391;
            end;
            v394.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_393 ]]
                return v_u_393;
            end;
            return v394;
        end)()))
    end;
    v_u_16.key_itr = function(_) --[[ Name: key_itr ]] --[[ Line: 706 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        return v_u_17:key_itr();
    end;
    v_u_16.contains_title_for_id = function(_, p395) --[[ Name: contains_title_for_id ]] --[[ Line: 707 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        return v_u_17:contains(p395);
    end;
    v_u_16.add_title_for_id = function(_, p396, p397) --[[ Name: add_title_for_id ]] --[[ Line: 709 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        p397:set_title_id(p396)
        v_u_17:add(p396, p397)
    end;
    v_u_16.get_default_title = function(_) --[[ Name: get_default_title ]] --[[ Line: 715 ]]
        --[[ Upvalues: (ref 1): v_u_9 ]]
        return v_u_9;
    end;
    v_u_16.get_title_for_id = function(_, p398) --[[ Name: get_title_for_id ]] --[[ Line: 717 ]]
        --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_9 ]]
        local v399 = v_u_17:get(p398)
        if v399 == nil then
            return v_u_9;
        else
            return v399;
        end;
    end;
    v_u_16.get_titledatabase_info = function(_) --[[ Name: get_titledatabase_info ]] --[[ Line: 730 ]]
        --[[ Upvalues: (copy 1): v_u_17 ]]
        local v400 = {}
        for v401, v402 in v_u_17:key_itr() do
            v400[#v400 + 1] = {
                ["title_id"] = v401,
                ["name"] = v402:get_name()
            }
        end;
        return v400;
    end;
    f_cons()
    return v_u_16;
end;
local v_u_403 = v_u_4:new()
v_u_4.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 748 ]]
    --[[ Upvalues: (copy 1): v_u_403 ]]
    return v_u_403;
end;
return v_u_4;
