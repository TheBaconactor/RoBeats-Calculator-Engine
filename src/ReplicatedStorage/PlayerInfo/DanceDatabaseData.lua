-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
return {
    ["add_dance_data"] = function(_, p_u_3, p_u_4) --[[ Name: add_dance_data ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        p_u_3:add_dance_for_id(1, ((function() --[[ Line: 14 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v5 = p_u_4.DanceInfoBase:new()
            v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 16 ]]
                return "Tantrum";
            end;
            v5.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 17 ]]
                return "";
            end;
            v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 18 ]]
                return "rbxassetid://2993990346";
            end;
            v5.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 19 ]]
                return "rbxassetid://713285606";
            end;
            v5.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 20 ]]
                return true;
            end;
            v5.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 21 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v5;
        end)()))
        p_u_3:add_dance_for_id(2, ((function() --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v6 = p_u_4.DanceInfoBase:new()
            v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 27 ]]
                return "Dizzy Fall";
            end;
            v6.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 28 ]]
                return "";
            end;
            v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 29 ]]
                return "rbxassetid://2993990427";
            end;
            v6.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 30 ]]
                return "rbxassetid://713231237";
            end;
            v6.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 31 ]]
                return true;
            end;
            v6.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 32 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v6;
        end)()))
        p_u_3:add_dance_for_id(3, ((function() --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v7 = p_u_4.DanceInfoBase:new()
            v7.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 38 ]]
                return "Sigh";
            end;
            v7.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 39 ]]
                return "";
            end;
            v7.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 40 ]]
                return "rbxassetid://2993990264";
            end;
            v7.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 41 ]]
                return "rbxassetid://710037303";
            end;
            v7.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 42 ]]
                return true;
            end;
            v7.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 43 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v7;
        end)()))
        p_u_3:add_dance_for_id(4, ((function() --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v8 = p_u_4.DanceInfoBase:new()
            v8.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 49 ]]
                return "Sway";
            end;
            v8.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 50 ]]
                return "";
            end;
            v8.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
                return "rbxassetid://2993990346";
            end;
            v8.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 52 ]]
                return "rbxassetid://705870851";
            end;
            v8.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 53 ]]
                return true;
            end;
            v8.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 54 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v8;
        end)()))
        p_u_3:add_dance_for_id(5, ((function() --[[ Line: 58 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v9 = p_u_4.DanceInfoBase:new()
            v9.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 60 ]]
                return "Ta-Dah!";
            end;
            v9.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 61 ]]
                return "";
            end;
            v9.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 62 ]]
                return "rbxassetid://2993990385";
            end;
            v9.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 63 ]]
                return "rbxassetid://711635385";
            end;
            v9.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 64 ]]
                return true;
            end;
            v9.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 65 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v9;
        end)()))
        p_u_3:add_dance_for_id(6, ((function() --[[ Line: 69 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v10 = p_u_4.DanceInfoBase:new()
            v10.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 71 ]]
                return "Four Step";
            end;
            v10.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 72 ]]
                return "";
            end;
            v10.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 73 ]]
                return "rbxassetid://2993241780";
            end;
            v10.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 74 ]]
                return "rbxassetid://716156761";
            end;
            v10.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 75 ]]
                return true;
            end;
            v10.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 76 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v10;
        end)()))
        p_u_3:add_dance_for_id(7, ((function() --[[ Line: 80 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v11 = p_u_4.DanceInfoBase:new()
            v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 82 ]]
                return "Wave";
            end;
            v11.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 83 ]]
                return "";
            end;
            v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 84 ]]
                return "rbxassetid://2993990385";
            end;
            v11.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 85 ]]
                return "rbxassetid://716494029";
            end;
            v11.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 86 ]]
                return true;
            end;
            v11.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 87 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v11;
        end)()))
        p_u_3:add_dance_for_id(8, ((function() --[[ Line: 91 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v12 = p_u_4.DanceInfoBase:new()
            v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 93 ]]
                return "Old School Shuffle";
            end;
            v12.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 94 ]]
                return "";
            end;
            v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 95 ]]
                return "rbxassetid://2993990307";
            end;
            v12.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 96 ]]
                return "rbxassetid://718420920";
            end;
            v12.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 97 ]]
                return true;
            end;
            v12.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v12;
        end)()))
        p_u_3:add_dance_for_id(9, ((function() --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v13 = p_u_4.DanceInfoBase:new()
            v13.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 104 ]]
                return "Hip Hop Sway";
            end;
            v13.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 105 ]]
                return "";
            end;
            v13.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 106 ]]
                return "rbxassetid://2993990264";
            end;
            v13.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 107 ]]
                return "rbxassetid://717481497";
            end;
            v13.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 108 ]]
                return true;
            end;
            v13.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 109 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v13;
        end)()))
        p_u_3:add_dance_for_id(10, ((function() --[[ Line: 113 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v14 = p_u_4.DanceInfoBase:new()
            v14.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 115 ]]
                return "Bounce";
            end;
            v14.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 116 ]]
                return "";
            end;
            v14.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 117 ]]
                return "rbxassetid://2993990307";
            end;
            v14.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 118 ]]
                return "rbxassetid://721463188";
            end;
            v14.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 119 ]]
                return true;
            end;
            v14.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 120 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Idle;
            end;
            return v14;
        end)()))
        p_u_3:add_dance_for_id(11, ((function() --[[ Line: 124 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v15 = p_u_4.DanceInfoBase:new()
            v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 126 ]]
                return "Breakdance";
            end;
            v15.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 127 ]]
                return "";
            end;
            v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 128 ]]
                return "rbxassetid://2993990427";
            end;
            v15.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 129 ]]
                return "rbxassetid://731452379";
            end;
            v15.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 130 ]]
                return true;
            end;
            v15.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 131 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v15;
        end)()))
        p_u_3:add_dance_for_id(12, ((function() --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v16 = p_u_4.DanceInfoBase:new()
            v16.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 137 ]]
                return "Break Spin";
            end;
            v16.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 138 ]]
                return "";
            end;
            v16.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 139 ]]
                return "rbxassetid://2993990427";
            end;
            v16.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 140 ]]
                return "rbxassetid://732270556";
            end;
            v16.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 141 ]]
                return true;
            end;
            v16.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 142 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v16;
        end)()))
        p_u_3:add_dance_for_id(13, ((function() --[[ Line: 146 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v17 = p_u_4.DanceInfoBase:new()
            v17.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 148 ]]
                return "Orange Justice";
            end;
            v17.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 149 ]]
                return "";
            end;
            v17.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 150 ]]
                return "rbxassetid://2993990346";
            end;
            v17.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 151 ]]
                return "rbxassetid://1691195191";
            end;
            v17.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 152 ]]
                return true;
            end;
            v17.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v17;
        end)()))
        p_u_3:add_dance_for_id(14, ((function() --[[ Line: 157 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v18 = p_u_4.DanceInfoBase:new()
            v18.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 159 ]]
                return "Happy Go Lucky";
            end;
            v18.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 160 ]]
                return "";
            end;
            v18.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 161 ]]
                return "rbxassetid://2993241780";
            end;
            v18.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 162 ]]
                return "rbxassetid://507771019";
            end;
            v18.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 163 ]]
                return true;
            end;
            v18.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 164 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v18;
        end)()))
        p_u_3:add_dance_for_id(15, ((function() --[[ Line: 168 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v19 = p_u_4.DanceInfoBase:new()
            v19.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 170 ]]
                return "The Wave";
            end;
            v19.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 171 ]]
                return "";
            end;
            v19.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 172 ]]
                return "rbxassetid://2993990385";
            end;
            v19.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 173 ]]
                return "rbxassetid://507776043";
            end;
            v19.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 174 ]]
                return true;
            end;
            v19.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 175 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v19;
        end)()))
        p_u_3:add_dance_for_id(16, ((function() --[[ Line: 179 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_1 ]]
            local v20 = p_u_4.DanceInfoBase:new()
            v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 181 ]]
                return "Smooth Groovin\'";
            end;
            v20.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 182 ]]
                return "";
            end;
            v20.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 183 ]]
                return "rbxassetid://2993990307";
            end;
            v20.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 184 ]]
                return "rbxassetid://507777268";
            end;
            v20.is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 185 ]]
                return true;
            end;
            v20.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 186 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v20;
        end)()))
        p_u_3:add_dance_for_id(17, ((function() --[[ Line: 192 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v21 = p_u_4.DanceInfoBase:new()
            v21.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 194 ]]
                return "Break Boy";
            end;
            v21.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 195 ]]
                return "";
            end;
            v21.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 196 ]]
                return "rbxassetid://2993990264";
            end;
            v21.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 197 ]]
                return "rbxassetid://5212039101";
            end;
            v21.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 198 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v21.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 199 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v21;
        end)()))
        p_u_3:add_dance_for_id(18, ((function() --[[ Line: 202 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v22 = p_u_4.DanceInfoBase:new()
            v22.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 204 ]]
                return "Arabian Night";
            end;
            v22.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 205 ]]
                return "";
            end;
            v22.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 206 ]]
                return "rbxassetid://2993990307";
            end;
            v22.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 207 ]]
                return "rbxassetid://5212042351";
            end;
            v22.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 208 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v22.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 209 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v22;
        end)()))
        p_u_3:add_dance_for_id(19, ((function() --[[ Line: 212 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v23 = p_u_4.DanceInfoBase:new()
            v23.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 214 ]]
                return "That\'s the Breaks";
            end;
            v23.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 215 ]]
                return "";
            end;
            v23.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 216 ]]
                return "rbxassetid://2993990427";
            end;
            v23.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 217 ]]
                return "rbxassetid://5212046464";
            end;
            v23.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 218 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v23.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 219 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v23;
        end)()))
        p_u_3:add_dance_for_id(20, ((function() --[[ Line: 222 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v24 = p_u_4.DanceInfoBase:new()
            v24.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 224 ]]
                return "Free Stylin\'";
            end;
            v24.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 225 ]]
                return "";
            end;
            v24.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 226 ]]
                return "rbxassetid://2993990346";
            end;
            v24.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 227 ]]
                return "rbxassetid://3238481223";
            end;
            v24.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 228 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v24.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 229 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v24;
        end)()))
        p_u_3:add_dance_for_id(21, ((function() --[[ Line: 232 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v25 = p_u_4.DanceInfoBase:new()
            v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 234 ]]
                return "The Brooklyn";
            end;
            v25.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 235 ]]
                return "";
            end;
            v25.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 236 ]]
                return "rbxassetid://2993241780";
            end;
            v25.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 237 ]]
                return "rbxassetid://5212048202";
            end;
            v25.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 238 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v25.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 239 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v25;
        end)()))
        p_u_3:add_dance_for_id(22, ((function() --[[ Line: 242 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v26 = p_u_4.DanceInfoBase:new()
            v26.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 244 ]]
                return "Can Can";
            end;
            v26.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 245 ]]
                return "";
            end;
            v26.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 246 ]]
                return "rbxassetid://2993990346";
            end;
            v26.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 247 ]]
                return "rbxassetid://5212049804";
            end;
            v26.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 248 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v26.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 249 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v26;
        end)()))
        p_u_3:add_dance_for_id(23, ((function() --[[ Line: 252 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v27 = p_u_4.DanceInfoBase:new()
            v27.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 254 ]]
                return "Chicken Dance";
            end;
            v27.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 255 ]]
                return "";
            end;
            v27.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 256 ]]
                return "rbxassetid://2993990307";
            end;
            v27.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 257 ]]
                return "rbxassetid://5212051624";
            end;
            v27.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 258 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v27.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 259 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v27;
        end)()))
        p_u_3:add_dance_for_id(24, ((function() --[[ Line: 262 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v28 = p_u_4.DanceInfoBase:new()
            v28.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 264 ]]
                return "Hop & Step";
            end;
            v28.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 265 ]]
                return "";
            end;
            v28.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 266 ]]
                return "rbxassetid://2993990385";
            end;
            v28.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 267 ]]
                return "rbxassetid://5212054142";
            end;
            v28.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 268 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v28.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 269 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v28;
        end)()))
        p_u_3:add_dance_for_id(25, ((function() --[[ Line: 272 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v29 = p_u_4.DanceInfoBase:new()
            v29.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 274 ]]
                return "Side Stepper";
            end;
            v29.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 275 ]]
                return "";
            end;
            v29.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 276 ]]
                return "rbxassetid://2993990264";
            end;
            v29.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 277 ]]
                return "rbxassetid://5212056186";
            end;
            v29.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 278 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v29.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 279 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v29;
        end)()))
        p_u_3:add_dance_for_id(26, ((function() --[[ Line: 282 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v30 = p_u_4.DanceInfoBase:new()
            v30.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 284 ]]
                return "Smug Dance";
            end;
            v30.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 285 ]]
                return "";
            end;
            v30.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 286 ]]
                return "rbxassetid://2993241780";
            end;
            v30.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 287 ]]
                return "rbxassetid://5683836095";
            end;
            v30.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 288 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v30.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 289 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v30;
        end)()))
        p_u_3:add_dance_for_id(27, ((function() --[[ Line: 292 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v31 = p_u_4.DanceInfoBase:new()
            v31.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 294 ]]
                return "Capoeira Kick";
            end;
            v31.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 295 ]]
                return "";
            end;
            v31.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 296 ]]
                return "rbxassetid://2993990427";
            end;
            v31.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 297 ]]
                return "rbxassetid://3192239903";
            end;
            v31.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 298 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v31.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 299 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v31;
        end)()))
        p_u_3:add_dance_for_id(28, ((function() --[[ Line: 302 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v32 = p_u_4.DanceInfoBase:new()
            v32.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 304 ]]
                return "Footwerk";
            end;
            v32.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 305 ]]
                return "";
            end;
            v32.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 306 ]]
                return "rbxassetid://2993990427";
            end;
            v32.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 307 ]]
                return "rbxassetid://5212060608";
            end;
            v32.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 308 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v32.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v32;
        end)()))
        p_u_3:add_dance_for_id(29, ((function() --[[ Line: 312 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v33 = p_u_4.DanceInfoBase:new()
            v33.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 314 ]]
                return "Break Circle";
            end;
            v33.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 315 ]]
                return "";
            end;
            v33.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 316 ]]
                return "rbxassetid://2993990427";
            end;
            v33.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 317 ]]
                return "rbxassetid://5212062551";
            end;
            v33.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 318 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v33.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 319 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v33;
        end)()))
        p_u_3:add_dance_for_id(30, ((function() --[[ Line: 322 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v34 = p_u_4.DanceInfoBase:new()
            v34.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 324 ]]
                return "Gangnam Style";
            end;
            v34.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 325 ]]
                return "";
            end;
            v34.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 326 ]]
                return "rbxassetid://2993990307";
            end;
            v34.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 327 ]]
                return "rbxassetid://5212064826";
            end;
            v34.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 328 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v34.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 329 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v34;
        end)()))
        p_u_3:add_dance_for_id(31, ((function() --[[ Line: 332 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v35 = p_u_4.DanceInfoBase:new()
            v35.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 334 ]]
                return "Head Banger";
            end;
            v35.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 335 ]]
                return "";
            end;
            v35.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 336 ]]
                return "rbxassetid://2993990264";
            end;
            v35.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 337 ]]
                return "rbxassetid://5212066619";
            end;
            v35.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 338 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v35.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 339 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v35;
        end)()))
        p_u_3:add_dance_for_id(32, ((function() --[[ Line: 342 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v36 = p_u_4.DanceInfoBase:new()
            v36.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 344 ]]
                return "Capoeira Sway";
            end;
            v36.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 345 ]]
                return "";
            end;
            v36.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 346 ]]
                return "rbxassetid://2993241780";
            end;
            v36.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 347 ]]
                return "rbxassetid://3190420354";
            end;
            v36.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 348 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v36.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 349 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v36;
        end)()))
        p_u_3:add_dance_for_id(33, ((function() --[[ Line: 352 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v37 = p_u_4.DanceInfoBase:new()
            v37.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 354 ]]
                return "Big Wave";
            end;
            v37.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 355 ]]
                return "";
            end;
            v37.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 356 ]]
                return "rbxassetid://2993990385";
            end;
            v37.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 357 ]]
                return "rbxassetid://5212069312";
            end;
            v37.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 358 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v37.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 359 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v37;
        end)()))
        p_u_3:add_dance_for_id(34, ((function() --[[ Line: 362 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v38 = p_u_4.DanceInfoBase:new()
            v38.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 364 ]]
                return "Air Guitar";
            end;
            v38.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 365 ]]
                return "";
            end;
            v38.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 366 ]]
                return "rbxassetid://2993990307";
            end;
            v38.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 367 ]]
                return "rbxassetid://5212071225";
            end;
            v38.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 368 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v38.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 369 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v38;
        end)()))
        p_u_3:add_dance_for_id(35, ((function() --[[ Line: 372 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v39 = p_u_4.DanceInfoBase:new()
            v39.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 374 ]]
                return "Tango Step";
            end;
            v39.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 375 ]]
                return "";
            end;
            v39.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 376 ]]
                return "rbxassetid://2993990307";
            end;
            v39.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 377 ]]
                return "rbxassetid://5212077454";
            end;
            v39.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 378 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v39.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 379 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v39;
        end)()))
        p_u_3:add_dance_for_id(36, ((function() --[[ Line: 382 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v40 = p_u_4.DanceInfoBase:new()
            v40.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 384 ]]
                return "Classic Sway";
            end;
            v40.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 385 ]]
                return "";
            end;
            v40.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 386 ]]
                return "rbxassetid://2993990264";
            end;
            v40.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 387 ]]
                return "rbxassetid://5212080819";
            end;
            v40.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 388 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v40.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 389 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v40;
        end)()))
        p_u_3:add_dance_for_id(37, ((function() --[[ Line: 392 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v41 = p_u_4.DanceInfoBase:new()
            v41.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 394 ]]
                return "Break Handstand";
            end;
            v41.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 395 ]]
                return "";
            end;
            v41.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 396 ]]
                return "rbxassetid://2993241780";
            end;
            v41.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 397 ]]
                return "rbxassetid://5212083032";
            end;
            v41.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 398 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v41.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 399 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v41;
        end)()))
        p_u_3:add_dance_for_id(38, ((function() --[[ Line: 402 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v42 = p_u_4.DanceInfoBase:new()
            v42.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 404 ]]
                return "Shake It Out";
            end;
            v42.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 405 ]]
                return "";
            end;
            v42.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 406 ]]
                return "rbxassetid://2993241780";
            end;
            v42.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 407 ]]
                return "rbxassetid://5212084867";
            end;
            v42.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 408 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v42.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 409 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v42;
        end)()))
        p_u_3:add_dance_for_id(39, ((function() --[[ Line: 412 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v43 = p_u_4.DanceInfoBase:new()
            v43.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 414 ]]
                return "The Shakeweight";
            end;
            v43.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 415 ]]
                return "";
            end;
            v43.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 416 ]]
                return "rbxassetid://2993990307";
            end;
            v43.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 417 ]]
                return "rbxassetid://5212087550";
            end;
            v43.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 418 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v43.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 419 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v43;
        end)()))
        p_u_3:add_dance_for_id(40, ((function() --[[ Line: 422 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v44 = p_u_4.DanceInfoBase:new()
            v44.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 424 ]]
                return "Step \'n Go";
            end;
            v44.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 425 ]]
                return "";
            end;
            v44.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 426 ]]
                return "rbxassetid://2993990307";
            end;
            v44.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 427 ]]
                return "rbxassetid://5212089219";
            end;
            v44.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 428 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v44.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 429 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v44;
        end)()))
        p_u_3:add_dance_for_id(41, ((function() --[[ Line: 432 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v45 = p_u_4.DanceInfoBase:new()
            v45.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 434 ]]
                return "Disco Shuffle";
            end;
            v45.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 435 ]]
                return "";
            end;
            v45.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 436 ]]
                return "rbxassetid://2993990264";
            end;
            v45.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 437 ]]
                return "rbxassetid://5212090967";
            end;
            v45.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 438 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v45.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 439 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v45;
        end)()))
        p_u_3:add_dance_for_id(42, ((function() --[[ Line: 442 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v46 = p_u_4.DanceInfoBase:new()
            v46.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 444 ]]
                return "Raise The Roof";
            end;
            v46.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 445 ]]
                return "";
            end;
            v46.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 446 ]]
                return "rbxassetid://2993990307";
            end;
            v46.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 447 ]]
                return "rbxassetid://5212093439";
            end;
            v46.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 448 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v46.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 449 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v46;
        end)()))
        p_u_3:add_dance_for_id(43, ((function() --[[ Line: 452 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v47 = p_u_4.DanceInfoBase:new()
            v47.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 454 ]]
                return "Cha-Cha";
            end;
            v47.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 455 ]]
                return "";
            end;
            v47.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 456 ]]
                return "rbxassetid://2993990346";
            end;
            v47.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 457 ]]
                return "rbxassetid://5212095260";
            end;
            v47.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 458 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v47.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 459 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v47;
        end)()))
        p_u_3:add_dance_for_id(44, ((function() --[[ Line: 462 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v48 = p_u_4.DanceInfoBase:new()
            v48.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 464 ]]
                return "Salt Shaker";
            end;
            v48.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 465 ]]
                return "";
            end;
            v48.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 466 ]]
                return "rbxassetid://2993990264";
            end;
            v48.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 467 ]]
                return "rbxassetid://5212097089";
            end;
            v48.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 468 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v48.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 469 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v48;
        end)()))
        p_u_3:add_dance_for_id(45, ((function() --[[ Line: 472 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v49 = p_u_4.DanceInfoBase:new()
            v49.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 474 ]]
                return "Smooth Criminal";
            end;
            v49.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 475 ]]
                return "";
            end;
            v49.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 476 ]]
                return "rbxassetid://2993241780";
            end;
            v49.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 477 ]]
                return "rbxassetid://5212098984";
            end;
            v49.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 478 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v49.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 479 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v49;
        end)()))
        p_u_3:add_dance_for_id(46, ((function() --[[ Line: 482 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v50 = p_u_4.DanceInfoBase:new()
            v50.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 484 ]]
                return "Dynamite";
            end;
            v50.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 485 ]]
                return "";
            end;
            v50.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 486 ]]
                return "rbxassetid://2993990264";
            end;
            v50.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 487 ]]
                return "rbxassetid://5212100592";
            end;
            v50.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 488 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v50.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 489 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v50;
        end)()))
        p_u_3:add_dance_for_id(47, ((function() --[[ Line: 492 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v51 = p_u_4.DanceInfoBase:new()
            v51.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 494 ]]
                return "The Shovel";
            end;
            v51.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 495 ]]
                return "";
            end;
            v51.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 496 ]]
                return "rbxassetid://2993990264";
            end;
            v51.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 497 ]]
                return "rbxassetid://5212102344";
            end;
            v51.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 498 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v51.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 499 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v51;
        end)()))
        p_u_3:add_dance_for_id(48, ((function() --[[ Line: 502 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v52 = p_u_4.DanceInfoBase:new()
            v52.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 504 ]]
                return "Saturday Night Fever";
            end;
            v52.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 505 ]]
                return "";
            end;
            v52.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 506 ]]
                return "rbxassetid://2993990385";
            end;
            v52.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 507 ]]
                return "rbxassetid://5212104334";
            end;
            v52.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 508 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v52.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 509 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v52;
        end)()))
        p_u_3:add_dance_for_id(49, ((function() --[[ Line: 512 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v53 = p_u_4.DanceInfoBase:new()
            v53.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 514 ]]
                return "The Crank";
            end;
            v53.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 515 ]]
                return "";
            end;
            v53.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 516 ]]
                return "rbxassetid://2993241780";
            end;
            v53.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 517 ]]
                return "rbxassetid://5212106109";
            end;
            v53.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 518 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v53.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 519 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v53;
        end)()))
        p_u_3:add_dance_for_id(50, ((function() --[[ Line: 522 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v54 = p_u_4.DanceInfoBase:new()
            v54.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 524 ]]
                return "Side Step Shuffle";
            end;
            v54.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 525 ]]
                return "";
            end;
            v54.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 526 ]]
                return "rbxassetid://2993241780";
            end;
            v54.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 527 ]]
                return "rbxassetid://5212110698";
            end;
            v54.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 528 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v54.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 529 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v54;
        end)()))
        p_u_3:add_dance_for_id(51, ((function() --[[ Line: 532 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v55 = p_u_4.DanceInfoBase:new()
            v55.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 534 ]]
                return "The Submarine";
            end;
            v55.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 535 ]]
                return "";
            end;
            v55.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 536 ]]
                return "rbxassetid://2993990264";
            end;
            v55.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 537 ]]
                return "rbxassetid://5212112292";
            end;
            v55.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 538 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v55.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 539 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v55;
        end)()))
        p_u_3:add_dance_for_id(52, ((function() --[[ Line: 542 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v56 = p_u_4.DanceInfoBase:new()
            v56.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 544 ]]
                return "The Anaconda";
            end;
            v56.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 545 ]]
                return "";
            end;
            v56.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 546 ]]
                return "rbxassetid://2993990264";
            end;
            v56.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 547 ]]
                return "rbxassetid://5212114559";
            end;
            v56.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 548 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v56.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 549 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v56;
        end)()))
        p_u_3:add_dance_for_id(53, ((function() --[[ Line: 552 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v57 = p_u_4.DanceInfoBase:new()
            v57.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 554 ]]
                return "Ricardo";
            end;
            v57.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 555 ]]
                return "";
            end;
            v57.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 556 ]]
                return "rbxassetid://2993990346";
            end;
            v57.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 557 ]]
                return "rbxassetid://5212116219";
            end;
            v57.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 558 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v57.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 559 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v57;
        end)()))
        p_u_3:add_dance_for_id(54, ((function() --[[ Line: 562 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v58 = p_u_4.DanceInfoBase:new()
            v58.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 564 ]]
                return "Wave Pump";
            end;
            v58.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 565 ]]
                return "";
            end;
            v58.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 566 ]]
                return "rbxassetid://2993990385";
            end;
            v58.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 567 ]]
                return "rbxassetid://5212117644";
            end;
            v58.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 568 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v58.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 569 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v58;
        end)()))
        p_u_3:add_dance_for_id(55, ((function() --[[ Line: 572 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v59 = p_u_4.DanceInfoBase:new()
            v59.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 574 ]]
                return "Jazz Step";
            end;
            v59.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 575 ]]
                return "";
            end;
            v59.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 576 ]]
                return "rbxassetid://2993241780";
            end;
            v59.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 577 ]]
                return "rbxassetid://5212119257";
            end;
            v59.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 578 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v59.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 579 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v59;
        end)()))
        p_u_3:add_dance_for_id(56, ((function() --[[ Line: 582 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v60 = p_u_4.DanceInfoBase:new()
            v60.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 584 ]]
                return "The Prance";
            end;
            v60.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 585 ]]
                return "";
            end;
            v60.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 586 ]]
                return "rbxassetid://2993241780";
            end;
            v60.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 587 ]]
                return "rbxassetid://5212120707";
            end;
            v60.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 588 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v60.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 589 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v60;
        end)()))
        p_u_3:add_dance_for_id(57, ((function() --[[ Line: 592 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v61 = p_u_4.DanceInfoBase:new()
            v61.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 594 ]]
                return "Pop Lock \'n Drop";
            end;
            v61.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 595 ]]
                return "";
            end;
            v61.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 596 ]]
                return "rbxassetid://2993241780";
            end;
            v61.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 597 ]]
                return "rbxassetid://5212122515";
            end;
            v61.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 598 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v61.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 599 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v61;
        end)()))
        p_u_3:add_dance_for_id(58, ((function() --[[ Line: 602 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v62 = p_u_4.DanceInfoBase:new()
            v62.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 604 ]]
                return "Silly Goose";
            end;
            v62.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 605 ]]
                return "";
            end;
            v62.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 606 ]]
                return "rbxassetid://2993990307";
            end;
            v62.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 607 ]]
                return "rbxassetid://5212127120";
            end;
            v62.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 608 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v62.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 609 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v62;
        end)()))
        p_u_3:add_dance_for_id(59, ((function() --[[ Line: 612 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v63 = p_u_4.DanceInfoBase:new()
            v63.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 614 ]]
                return "Head Movement";
            end;
            v63.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 615 ]]
                return "";
            end;
            v63.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 616 ]]
                return "rbxassetid://2993990346";
            end;
            v63.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 617 ]]
                return "rbxassetid://5212124901";
            end;
            v63.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 618 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v63.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 619 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v63;
        end)()))
        p_u_3:add_dance_for_id(60, ((function() --[[ Line: 622 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v64 = p_u_4.DanceInfoBase:new()
            v64.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 624 ]]
                return "Running Man";
            end;
            v64.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 625 ]]
                return "";
            end;
            v64.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 626 ]]
                return "rbxassetid://2993990385";
            end;
            v64.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 627 ]]
                return "rbxassetid://5212129055";
            end;
            v64.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 628 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v64.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 629 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v64;
        end)()))
        p_u_3:add_dance_for_id(61, ((function() --[[ Line: 632 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v65 = p_u_4.DanceInfoBase:new()
            v65.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 634 ]]
                return "The Matador";
            end;
            v65.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 635 ]]
                return "";
            end;
            v65.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 636 ]]
                return "rbxassetid://2993241780";
            end;
            v65.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 637 ]]
                return "rbxassetid://5212130463";
            end;
            v65.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 638 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v65.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 639 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v65;
        end)()))
        p_u_3:add_dance_for_id(62, ((function() --[[ Line: 642 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v66 = p_u_4.DanceInfoBase:new()
            v66.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 644 ]]
                return "Zumba";
            end;
            v66.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 645 ]]
                return "";
            end;
            v66.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 646 ]]
                return "rbxassetid://2993990264";
            end;
            v66.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 647 ]]
                return "rbxassetid://5212132346";
            end;
            v66.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 648 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v66.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 649 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v66;
        end)()))
        p_u_3:add_dance_for_id(63, ((function() --[[ Line: 652 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v67 = p_u_4.DanceInfoBase:new()
            v67.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 654 ]]
                return "Salsa For One";
            end;
            v67.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 655 ]]
                return "";
            end;
            v67.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 656 ]]
                return "rbxassetid://2993990264";
            end;
            v67.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 657 ]]
                return "rbxassetid://5212134286";
            end;
            v67.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 658 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v67.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 659 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v67;
        end)()))
        p_u_3:add_dance_for_id(64, ((function() --[[ Line: 662 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v68 = p_u_4.DanceInfoBase:new()
            v68.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 664 ]]
                return "The Latin";
            end;
            v68.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 665 ]]
                return "";
            end;
            v68.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 666 ]]
                return "rbxassetid://2993241780";
            end;
            v68.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 667 ]]
                return "rbxassetid://5212136207";
            end;
            v68.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 668 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v68.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 669 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v68;
        end)()))
        p_u_3:add_dance_for_id(65, ((function() --[[ Line: 672 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v69 = p_u_4.DanceInfoBase:new()
            v69.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 674 ]]
                return "Latin Sway";
            end;
            v69.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 675 ]]
                return "";
            end;
            v69.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 676 ]]
                return "rbxassetid://2993241780";
            end;
            v69.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 677 ]]
                return "rbxassetid://5212138040";
            end;
            v69.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 678 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v69.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 679 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v69;
        end)()))
        p_u_3:add_dance_for_id(66, ((function() --[[ Line: 682 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v70 = p_u_4.DanceInfoBase:new()
            v70.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 684 ]]
                return "Cantina";
            end;
            v70.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 685 ]]
                return "";
            end;
            v70.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 686 ]]
                return "rbxassetid://2993990385";
            end;
            v70.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 687 ]]
                return "rbxassetid://5212139732";
            end;
            v70.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 688 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v70.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 689 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v70;
        end)()))
        p_u_3:add_dance_for_id(67, ((function() --[[ Line: 692 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v71 = p_u_4.DanceInfoBase:new()
            v71.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 694 ]]
                return "The Cuban";
            end;
            v71.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 695 ]]
                return "";
            end;
            v71.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 696 ]]
                return "rbxassetid://2993990264";
            end;
            v71.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 697 ]]
                return "rbxassetid://5212141221";
            end;
            v71.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 698 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v71.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 699 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v71;
        end)()))
        p_u_3:add_dance_for_id(68, ((function() --[[ Line: 702 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v72 = p_u_4.DanceInfoBase:new()
            v72.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 704 ]]
                return "Pull It!";
            end;
            v72.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 705 ]]
                return "";
            end;
            v72.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 706 ]]
                return "rbxassetid://2993990346";
            end;
            v72.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 707 ]]
                return "rbxassetid://5212142868";
            end;
            v72.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 708 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v72.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 709 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v72;
        end)()))
        p_u_3:add_dance_for_id(69, ((function() --[[ Line: 712 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v73 = p_u_4.DanceInfoBase:new()
            v73.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 714 ]]
                return "Exotica";
            end;
            v73.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 715 ]]
                return "";
            end;
            v73.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 716 ]]
                return "rbxassetid://2993990264";
            end;
            v73.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 717 ]]
                return "rbxassetid://5212144403";
            end;
            v73.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 718 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v73.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 719 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v73;
        end)()))
        p_u_3:add_dance_for_id(70, ((function() --[[ Line: 722 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v74 = p_u_4.DanceInfoBase:new()
            v74.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 724 ]]
                return "El Burro";
            end;
            v74.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 725 ]]
                return "";
            end;
            v74.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 726 ]]
                return "rbxassetid://2993241780";
            end;
            v74.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 727 ]]
                return "rbxassetid://5212146128";
            end;
            v74.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 728 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v74.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 729 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v74;
        end)()))
        p_u_3:add_dance_for_id(71, ((function() --[[ Line: 732 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v75 = p_u_4.DanceInfoBase:new()
            v75.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 734 ]]
                return "Flamenco";
            end;
            v75.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 735 ]]
                return "";
            end;
            v75.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 736 ]]
                return "rbxassetid://2993990264";
            end;
            v75.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 737 ]]
                return "rbxassetid://5212147811";
            end;
            v75.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 738 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v75.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 739 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v75;
        end)()))
        p_u_3:add_dance_for_id(72, ((function() --[[ Line: 742 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v76 = p_u_4.DanceInfoBase:new()
            v76.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 744 ]]
                return "Slow \'n Steady";
            end;
            v76.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 745 ]]
                return "";
            end;
            v76.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 746 ]]
                return "rbxassetid://2993990264";
            end;
            v76.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 747 ]]
                return "rbxassetid://5212149875";
            end;
            v76.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 748 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v76.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 749 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v76;
        end)()))
        p_u_3:add_dance_for_id(73, ((function() --[[ Line: 752 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v77 = p_u_4.DanceInfoBase:new()
            v77.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 754 ]]
                return "Row The Boat";
            end;
            v77.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 755 ]]
                return "";
            end;
            v77.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 756 ]]
                return "rbxassetid://2993990346";
            end;
            v77.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 757 ]]
                return "rbxassetid://5212151417";
            end;
            v77.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 758 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v77.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 759 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v77;
        end)()))
        p_u_3:add_dance_for_id(74, ((function() --[[ Line: 762 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v78 = p_u_4.DanceInfoBase:new()
            v78.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 764 ]]
                return "Spinning Splitz";
            end;
            v78.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 765 ]]
                return "";
            end;
            v78.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 766 ]]
                return "rbxassetid://2993990427";
            end;
            v78.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 767 ]]
                return "rbxassetid://5212154751";
            end;
            v78.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 768 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v78.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 769 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v78;
        end)()))
        p_u_3:add_dance_for_id(75, ((function() --[[ Line: 772 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v79 = p_u_4.DanceInfoBase:new()
            v79.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 774 ]]
                return "Spinning Top";
            end;
            v79.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 775 ]]
                return "";
            end;
            v79.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 776 ]]
                return "rbxassetid://2993990427";
            end;
            v79.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 777 ]]
                return "rbxassetid://5212156737";
            end;
            v79.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 778 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v79.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 779 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v79;
        end)()))
        p_u_3:add_dance_for_id(76, ((function() --[[ Line: 782 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v80 = p_u_4.DanceInfoBase:new()
            v80.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 784 ]]
                return "Cross Step";
            end;
            v80.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 785 ]]
                return "";
            end;
            v80.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 786 ]]
                return "rbxassetid://2993990264";
            end;
            v80.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 787 ]]
                return "rbxassetid://5212159003";
            end;
            v80.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 788 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v80.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 789 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v80;
        end)()))
        p_u_3:add_dance_for_id(77, ((function() --[[ Line: 792 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v81 = p_u_4.DanceInfoBase:new()
            v81.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 794 ]]
                return "The King Tut";
            end;
            v81.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 795 ]]
                return "";
            end;
            v81.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 796 ]]
                return "rbxassetid://2993241780";
            end;
            v81.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 797 ]]
                return "rbxassetid://5212160588";
            end;
            v81.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 798 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v81.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 799 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v81;
        end)()))
        p_u_3:add_dance_for_id(78, ((function() --[[ Line: 802 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v82 = p_u_4.DanceInfoBase:new()
            v82.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 804 ]]
                return "The Stinky Leg";
            end;
            v82.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 805 ]]
                return "";
            end;
            v82.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 806 ]]
                return "rbxassetid://2993990264";
            end;
            v82.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 807 ]]
                return "rbxassetid://5212162697";
            end;
            v82.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 808 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v82.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 809 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v82;
        end)()))
        p_u_3:add_dance_for_id(79, ((function() --[[ Line: 812 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v83 = p_u_4.DanceInfoBase:new()
            v83.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 814 ]]
                return "The 4 Step";
            end;
            v83.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 815 ]]
                return "";
            end;
            v83.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 816 ]]
                return "rbxassetid://2993241780";
            end;
            v83.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 817 ]]
                return "rbxassetid://5212164005";
            end;
            v83.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 818 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v83.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 819 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v83;
        end)()))
        p_u_3:add_dance_for_id(80, ((function() --[[ Line: 822 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v84 = p_u_4.DanceInfoBase:new()
            v84.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 824 ]]
                return "Beat Step";
            end;
            v84.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 825 ]]
                return "";
            end;
            v84.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 826 ]]
                return "rbxassetid://2993990346";
            end;
            v84.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 827 ]]
                return "rbxassetid://5212165188";
            end;
            v84.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 828 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v84.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 829 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v84;
        end)()))
        p_u_3:add_dance_for_id(81, ((function() --[[ Line: 832 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v85 = p_u_4.DanceInfoBase:new()
            v85.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 834 ]]
                return "Disco Step";
            end;
            v85.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 835 ]]
                return "";
            end;
            v85.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 836 ]]
                return "rbxassetid://2993990346";
            end;
            v85.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 837 ]]
                return "rbxassetid://5212166421";
            end;
            v85.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 838 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v85.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 839 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v85;
        end)()))
        p_u_3:add_dance_for_id(82, ((function() --[[ Line: 842 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v86 = p_u_4.DanceInfoBase:new()
            v86.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 844 ]]
                return "The Balboa";
            end;
            v86.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 845 ]]
                return "";
            end;
            v86.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 846 ]]
                return "rbxassetid://2993241780";
            end;
            v86.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 847 ]]
                return "rbxassetid://5212168012";
            end;
            v86.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 848 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v86.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 849 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v86;
        end)()))
        p_u_3:add_dance_for_id(83, ((function() --[[ Line: 852 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v87 = p_u_4.DanceInfoBase:new()
            v87.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 854 ]]
                return "The Wave";
            end;
            v87.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 855 ]]
                return "";
            end;
            v87.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 856 ]]
                return "rbxassetid://2993990385";
            end;
            v87.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 857 ]]
                return "rbxassetid://5212169431";
            end;
            v87.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 858 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v87.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 859 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v87;
        end)()))
        p_u_3:add_dance_for_id(84, ((function() --[[ Line: 862 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v88 = p_u_4.DanceInfoBase:new()
            v88.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 864 ]]
                return "YMCA";
            end;
            v88.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 865 ]]
                return "";
            end;
            v88.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 866 ]]
                return "rbxassetid://2993241780";
            end;
            v88.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 867 ]]
                return "rbxassetid://5212170769";
            end;
            v88.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 868 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v88.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 869 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v88;
        end)()))
        p_u_3:add_dance_for_id(85, ((function() --[[ Line: 872 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v89 = p_u_4.DanceInfoBase:new()
            v89.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 874 ]]
                return "Hype";
            end;
            v89.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 875 ]]
                return "";
            end;
            v89.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 876 ]]
                return "rbxassetid://2993990346";
            end;
            v89.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 877 ]]
                return "rbxassetid://3238482975";
            end;
            v89.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 878 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v89.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 879 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v89;
        end)()))
        p_u_3:add_dance_for_id(86, ((function() --[[ Line: 882 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v90 = p_u_4.DanceInfoBase:new()
            v90.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 884 ]]
                return "Floss";
            end;
            v90.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 885 ]]
                return "";
            end;
            v90.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 886 ]]
                return "rbxassetid://2993990264";
            end;
            v90.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 887 ]]
                return "rbxassetid://3238480206";
            end;
            v90.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 888 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v90.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 889 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v90;
        end)()))
        p_u_3:add_dance_for_id(87, ((function() --[[ Line: 892 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v91 = p_u_4.DanceInfoBase:new()
            v91.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 894 ]]
                return "Electro Shuffle";
            end;
            v91.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 895 ]]
                return "";
            end;
            v91.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 896 ]]
                return "rbxassetid://2993241780";
            end;
            v91.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 897 ]]
                return "rbxassetid://3238477115";
            end;
            v91.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 898 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v91.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 899 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v91;
        end)()))
        p_u_3:add_dance_for_id(88, ((function() --[[ Line: 902 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v92 = p_u_4.DanceInfoBase:new()
            v92.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 904 ]]
                return "Take The L";
            end;
            v92.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 905 ]]
                return "";
            end;
            v92.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 906 ]]
                return "rbxassetid://2993990346";
            end;
            v92.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 907 ]]
                return "rbxassetid://3238486128";
            end;
            v92.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 908 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v92.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 909 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v92;
        end)()))
        p_u_3:add_dance_for_id(89, ((function() --[[ Line: 913 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v93 = p_u_4.DanceInfoBase:new()
            v93.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 915 ]]
                return "Hard Rock Guitar";
            end;
            v93.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 916 ]]
                return "";
            end;
            v93.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 917 ]]
                return "rbxassetid://2993990346";
            end;
            v93.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 918 ]]
                return "rbxassetid://4326693389";
            end;
            v93.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 919 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v93.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 920 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v93;
        end)()))
        p_u_3:add_dance_for_id(90, ((function() --[[ Line: 923 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v94 = p_u_4.DanceInfoBase:new()
            v94.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 925 ]]
                return "Jump For Joy";
            end;
            v94.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 926 ]]
                return "";
            end;
            v94.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 927 ]]
                return "rbxassetid://2993990385";
            end;
            v94.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 928 ]]
                return "rbxassetid://4326696854";
            end;
            v94.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 929 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v94.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 930 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v94;
        end)()))
        p_u_3:add_dance_for_id(91, ((function() --[[ Line: 933 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v95 = p_u_4.DanceInfoBase:new()
            v95.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 935 ]]
                return "Cha-Cha Returns";
            end;
            v95.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 936 ]]
                return "";
            end;
            v95.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 937 ]]
                return "rbxassetid://2993990307";
            end;
            v95.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 938 ]]
                return "rbxassetid://4326699426";
            end;
            v95.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 939 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v95.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 940 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v95;
        end)()))
        p_u_3:add_dance_for_id(92, ((function() --[[ Line: 943 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v96 = p_u_4.DanceInfoBase:new()
            v96.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 945 ]]
                return "Strike A Pose";
            end;
            v96.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 946 ]]
                return "";
            end;
            v96.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 947 ]]
                return "rbxassetid://2993990264";
            end;
            v96.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 948 ]]
                return "rbxassetid://4326700638";
            end;
            v96.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 949 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v96.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 950 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v96;
        end)()))
        p_u_3:add_dance_for_id(93, ((function() --[[ Line: 953 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v97 = p_u_4.DanceInfoBase:new()
            v97.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 955 ]]
                return "Jumping Jacks";
            end;
            v97.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 956 ]]
                return "";
            end;
            v97.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 957 ]]
                return "rbxassetid://2993990385";
            end;
            v97.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 958 ]]
                return "rbxassetid://4326703009";
            end;
            v97.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 959 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v97.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 960 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v97;
        end)()))
        p_u_3:add_dance_for_id(94, ((function() --[[ Line: 963 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v98 = p_u_4.DanceInfoBase:new()
            v98.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 965 ]]
                return "The Monkey";
            end;
            v98.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 966 ]]
                return "";
            end;
            v98.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 967 ]]
                return "rbxassetid://2993241780";
            end;
            v98.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 968 ]]
                return "rbxassetid://4326706428";
            end;
            v98.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 969 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v98.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 970 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v98;
        end)()))
        p_u_3:add_dance_for_id(95, ((function() --[[ Line: 973 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v99 = p_u_4.DanceInfoBase:new()
            v99.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 975 ]]
                return "I, Robot";
            end;
            v99.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 976 ]]
                return "";
            end;
            v99.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 977 ]]
                return "rbxassetid://2993241780";
            end;
            v99.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 978 ]]
                return "rbxassetid://4326708130";
            end;
            v99.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 979 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v99.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 980 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v99;
        end)()))
        p_u_3:add_dance_for_id(96, ((function() --[[ Line: 983 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v100 = p_u_4.DanceInfoBase:new()
            v100.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 985 ]]
                return "Bashful";
            end;
            v100.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 986 ]]
                return "";
            end;
            v100.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 987 ]]
                return "rbxassetid://2993990346";
            end;
            v100.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 988 ]]
                return "rbxassetid://4326709909";
            end;
            v100.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 989 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v100.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 990 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v100;
        end)()))
        p_u_3:add_dance_for_id(97, ((function() --[[ Line: 993 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v101 = p_u_4.DanceInfoBase:new()
            v101.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 995 ]]
                return "T-Pose";
            end;
            v101.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 996 ]]
                return "";
            end;
            v101.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 997 ]]
                return "rbxassetid://2993990385";
            end;
            v101.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 998 ]]
                return "rbxassetid://4326711509";
            end;
            v101.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 999 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v101.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1000 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v101;
        end)()))
        p_u_3:add_dance_for_id(98, ((function() --[[ Line: 1003 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v102 = p_u_4.DanceInfoBase:new()
            v102.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1005 ]]
                return "Top Rocker";
            end;
            v102.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1006 ]]
                return "";
            end;
            v102.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1007 ]]
                return "rbxassetid://2993241780";
            end;
            v102.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1008 ]]
                return "rbxassetid://4326714106";
            end;
            v102.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1009 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v102.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1010 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v102;
        end)()))
        p_u_3:add_dance_for_id(99, ((function() --[[ Line: 1013 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v103 = p_u_4.DanceInfoBase:new()
            v103.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1015 ]]
                return "Twirl";
            end;
            v103.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1016 ]]
                return "";
            end;
            v103.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1017 ]]
                return "rbxassetid://2993990385";
            end;
            v103.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1018 ]]
                return "rbxassetid://4326717080";
            end;
            v103.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1019 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v103.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1020 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v103;
        end)()))
        p_u_3:add_dance_for_id(100, ((function() --[[ Line: 1023 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v104 = p_u_4.DanceInfoBase:new()
            v104.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1025 ]]
                return "Buckets";
            end;
            v104.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1026 ]]
                return "";
            end;
            v104.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1027 ]]
                return "rbxassetid://2993990346";
            end;
            v104.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1028 ]]
                return "rbxassetid://4326836279";
            end;
            v104.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1029 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v104.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1030 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v104;
        end)()))
        p_u_3:add_dance_for_id(101, ((function() --[[ Line: 1033 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v105 = p_u_4.DanceInfoBase:new()
            v105.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1035 ]]
                return "On The Line";
            end;
            v105.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1036 ]]
                return "";
            end;
            v105.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1037 ]]
                return "rbxassetid://2993990346";
            end;
            v105.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1038 ]]
                return "rbxassetid://4326838794";
            end;
            v105.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1039 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v105.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1040 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v105;
        end)()))
        p_u_3:add_dance_for_id(102, ((function() --[[ Line: 1043 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v106 = p_u_4.DanceInfoBase:new()
            v106.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1045 ]]
                return "Make Some Noise";
            end;
            v106.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1046 ]]
                return "";
            end;
            v106.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1047 ]]
                return "rbxassetid://2993990385";
            end;
            v106.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1048 ]]
                return "rbxassetid://4326840631";
            end;
            v106.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1049 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v106.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1050 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v106;
        end)()))
        p_u_3:add_dance_for_id(103, ((function() --[[ Line: 1053 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v107 = p_u_4.DanceInfoBase:new()
            v107.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1055 ]]
                return "The Fresh Prince";
            end;
            v107.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1056 ]]
                return "";
            end;
            v107.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1057 ]]
                return "rbxassetid://2993241780";
            end;
            v107.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1058 ]]
                return "rbxassetid://4326843104";
            end;
            v107.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1059 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v107.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1060 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v107;
        end)()))
        p_u_3:add_dance_for_id(104, ((function() --[[ Line: 1063 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v108 = p_u_4.DanceInfoBase:new()
            v108.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1065 ]]
                return "Tree Pose";
            end;
            v108.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1066 ]]
                return "";
            end;
            v108.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1067 ]]
                return "rbxassetid://2993990427";
            end;
            v108.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1068 ]]
                return "rbxassetid://4326845525";
            end;
            v108.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1069 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v108.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1070 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v108;
        end)()))
        p_u_3:add_dance_for_id(105, ((function() --[[ Line: 1073 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v109 = p_u_4.DanceInfoBase:new()
            v109.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1075 ]]
                return "The Back Street";
            end;
            v109.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1076 ]]
                return "";
            end;
            v109.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1077 ]]
                return "rbxassetid://2993241780";
            end;
            v109.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1078 ]]
                return "rbxassetid://4326847523";
            end;
            v109.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1079 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v109.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1080 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v109;
        end)()))
        p_u_3:add_dance_for_id(106, ((function() --[[ Line: 1083 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v110 = p_u_4.DanceInfoBase:new()
            v110.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1085 ]]
                return "Hello, World!";
            end;
            v110.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1086 ]]
                return "";
            end;
            v110.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1087 ]]
                return "rbxassetid://2993990385";
            end;
            v110.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1088 ]]
                return "rbxassetid://4326849826";
            end;
            v110.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1089 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v110.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1090 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v110;
        end)()))
        p_u_3:add_dance_for_id(107, ((function() --[[ Line: 1093 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v111 = p_u_4.DanceInfoBase:new()
            v111.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1095 ]]
                return "Reel Big Fish";
            end;
            v111.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1096 ]]
                return "";
            end;
            v111.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1097 ]]
                return "rbxassetid://2993990307";
            end;
            v111.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1098 ]]
                return "rbxassetid://4326851717";
            end;
            v111.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1099 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v111.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1100 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v111;
        end)()))
        p_u_3:add_dance_for_id(108, ((function() --[[ Line: 1103 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v112 = p_u_4.DanceInfoBase:new()
            v112.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1105 ]]
                return "Tippity-Tap";
            end;
            v112.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1106 ]]
                return "";
            end;
            v112.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1107 ]]
                return "rbxassetid://2993990264";
            end;
            v112.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1108 ]]
                return "rbxassetid://4326855239";
            end;
            v112.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1109 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v112.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1110 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v112;
        end)()))
        p_u_3:add_dance_for_id(109, ((function() --[[ Line: 1113 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v113 = p_u_4.DanceInfoBase:new()
            v113.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1115 ]]
                return "(Don\'t) Rock the Boat";
            end;
            v113.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1116 ]]
                return "";
            end;
            v113.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1117 ]]
                return "rbxassetid://2993990264";
            end;
            v113.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1118 ]]
                return "rbxassetid://4326857155";
            end;
            v113.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1119 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v113.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1120 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v113;
        end)()))
        p_u_3:add_dance_for_id(110, ((function() --[[ Line: 1123 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v114 = p_u_4.DanceInfoBase:new()
            v114.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1125 ]]
                return "Clap Tap";
            end;
            v114.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1126 ]]
                return "";
            end;
            v114.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1127 ]]
                return "rbxassetid://2993990264";
            end;
            v114.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1128 ]]
                return "rbxassetid://4779613254";
            end;
            v114.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1129 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v114.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1130 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v114;
        end)()))
        p_u_3:add_dance_for_id(111, ((function() --[[ Line: 1133 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v115 = p_u_4.DanceInfoBase:new()
            v115.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1135 ]]
                return "Neko Yay";
            end;
            v115.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1136 ]]
                return "";
            end;
            v115.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1137 ]]
                return "rbxassetid://2993990385";
            end;
            v115.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1138 ]]
                return "rbxassetid://4779616698";
            end;
            v115.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1139 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v115.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1140 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v115;
        end)()))
        p_u_3:add_dance_for_id(112, ((function() --[[ Line: 1143 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v116 = p_u_4.DanceInfoBase:new()
            v116.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1145 ]]
                return "Muahahaha!!";
            end;
            v116.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1146 ]]
                return "";
            end;
            v116.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1147 ]]
                return "rbxassetid://2993990385";
            end;
            v116.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1148 ]]
                return "rbxassetid://4779619716";
            end;
            v116.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1149 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v116.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1150 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v116;
        end)()))
        p_u_3:add_dance_for_id(113, ((function() --[[ Line: 1153 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v117 = p_u_4.DanceInfoBase:new()
            v117.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1155 ]]
                return "Stretch the Legs";
            end;
            v117.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1156 ]]
                return "";
            end;
            v117.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1157 ]]
                return "rbxassetid://2993990385";
            end;
            v117.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1158 ]]
                return "rbxassetid://4779629421";
            end;
            v117.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1159 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v117.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1160 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v117;
        end)()))
        p_u_3:add_dance_for_id(114, ((function() --[[ Line: 1163 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v118 = p_u_4.DanceInfoBase:new()
            v118.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1165 ]]
                return "Power Up!";
            end;
            v118.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1166 ]]
                return "";
            end;
            v118.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1167 ]]
                return "rbxassetid://2993990346";
            end;
            v118.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1168 ]]
                return "rbxassetid://4779632468";
            end;
            v118.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1169 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v118.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1170 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v118;
        end)()))
        p_u_3:add_dance_for_id(115, ((function() --[[ Line: 1173 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v119 = p_u_4.DanceInfoBase:new()
            v119.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1175 ]]
                return "Sowwy~!";
            end;
            v119.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1176 ]]
                return "";
            end;
            v119.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1177 ]]
                return "rbxassetid://2993990346";
            end;
            v119.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1178 ]]
                return "rbxassetid://4779635994";
            end;
            v119.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1179 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v119.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1180 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v119;
        end)()))
        p_u_3:add_dance_for_id(116, ((function() --[[ Line: 1184 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v120 = p_u_4.DanceInfoBase:new()
            v120.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1186 ]]
                return "Addendum";
            end;
            v120.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1187 ]]
                return "";
            end;
            v120.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1188 ]]
                return "rbxassetid://2993241780";
            end;
            v120.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1189 ]]
                return "rbxassetid://5167292885";
            end;
            v120.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1190 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v120.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1191 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v120;
        end)()))
        p_u_3:add_dance_for_id(117, ((function() --[[ Line: 1194 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v121 = p_u_4.DanceInfoBase:new()
            v121.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1196 ]]
                return "(Just) Beat It!";
            end;
            v121.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1197 ]]
                return "";
            end;
            v121.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1198 ]]
                return "rbxassetid://2993241780";
            end;
            v121.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1199 ]]
                return "rbxassetid://5167300957";
            end;
            v121.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1200 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v121.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1201 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v121;
        end)()))
        p_u_3:add_dance_for_id(118, ((function() --[[ Line: 1204 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v122 = p_u_4.DanceInfoBase:new()
            v122.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1206 ]]
                return "Blame it on Boogie";
            end;
            v122.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1207 ]]
                return "";
            end;
            v122.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1208 ]]
                return "rbxassetid://2993990346";
            end;
            v122.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1209 ]]
                return "rbxassetid://5167304834";
            end;
            v122.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1210 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v122.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1211 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v122;
        end)()))
        p_u_3:add_dance_for_id(119, ((function() --[[ Line: 1214 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v123 = p_u_4.DanceInfoBase:new()
            v123.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1216 ]]
                return "Coffee Shuffle";
            end;
            v123.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1217 ]]
                return "";
            end;
            v123.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1218 ]]
                return "rbxassetid://2993990264";
            end;
            v123.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1219 ]]
                return "rbxassetid://5167307186";
            end;
            v123.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1220 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v123.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1221 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v123;
        end)()))
        p_u_3:add_dance_for_id(120, ((function() --[[ Line: 1224 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v124 = p_u_4.DanceInfoBase:new()
            v124.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1226 ]]
                return "Crank Dat";
            end;
            v124.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1227 ]]
                return "";
            end;
            v124.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1228 ]]
                return "rbxassetid://2993990385";
            end;
            v124.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1229 ]]
                return "rbxassetid://5167312098";
            end;
            v124.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1230 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v124.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1231 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v124;
        end)()))
        p_u_3:add_dance_for_id(121, ((function() --[[ Line: 1234 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v125 = p_u_4.DanceInfoBase:new()
            v125.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1236 ]]
                return "Wave and Slide";
            end;
            v125.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1237 ]]
                return "";
            end;
            v125.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1238 ]]
                return "rbxassetid://2993990385";
            end;
            v125.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1239 ]]
                return "rbxassetid://5167316671";
            end;
            v125.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1240 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v125.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1241 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v125;
        end)()))
        p_u_3:add_dance_for_id(122, ((function() --[[ Line: 1244 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v126 = p_u_4.DanceInfoBase:new()
            v126.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1246 ]]
                return "Feelin\' Good";
            end;
            v126.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1247 ]]
                return "";
            end;
            v126.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1248 ]]
                return "rbxassetid://2993990307";
            end;
            v126.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1249 ]]
                return "rbxassetid://5167321905";
            end;
            v126.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1250 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v126.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1251 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v126;
        end)()))
        p_u_3:add_dance_for_id(123, ((function() --[[ Line: 1254 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v127 = p_u_4.DanceInfoBase:new()
            v127.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1256 ]]
                return "Groove it, Gary!";
            end;
            v127.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1257 ]]
                return "";
            end;
            v127.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1258 ]]
                return "rbxassetid://2993241780";
            end;
            v127.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1259 ]]
                return "rbxassetid://5167330618";
            end;
            v127.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1260 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v127.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1261 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v127;
        end)()))
        p_u_3:add_dance_for_id(124, ((function() --[[ Line: 1264 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v128 = p_u_4.DanceInfoBase:new()
            v128.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1266 ]]
                return "Get Down";
            end;
            v128.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1267 ]]
                return "";
            end;
            v128.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1268 ]]
                return "rbxassetid://2993241780";
            end;
            v128.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1269 ]]
                return "rbxassetid://5167335552";
            end;
            v128.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1270 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v128.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1271 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v128;
        end)()))
        p_u_3:add_dance_for_id(125, ((function() --[[ Line: 1274 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v129 = p_u_4.DanceInfoBase:new()
            v129.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1276 ]]
                return "Glam Slam";
            end;
            v129.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1277 ]]
                return "";
            end;
            v129.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1278 ]]
                return "rbxassetid://2993990346";
            end;
            v129.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1279 ]]
                return "rbxassetid://5167339115";
            end;
            v129.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1280 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v129.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1281 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v129;
        end)()))
        p_u_3:add_dance_for_id(126, ((function() --[[ Line: 1284 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v130 = p_u_4.DanceInfoBase:new()
            v130.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1286 ]]
                return "Shots on Goal";
            end;
            v130.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1287 ]]
                return "";
            end;
            v130.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1288 ]]
                return "rbxassetid://2993990307";
            end;
            v130.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1289 ]]
                return "rbxassetid://5167341418";
            end;
            v130.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1290 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v130.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1291 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v130;
        end)()))
        p_u_3:add_dance_for_id(127, ((function() --[[ Line: 1294 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v131 = p_u_4.DanceInfoBase:new()
            v131.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1296 ]]
                return "With a Heart of Gold";
            end;
            v131.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1297 ]]
                return "";
            end;
            v131.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1298 ]]
                return "rbxassetid://2993990307";
            end;
            v131.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1299 ]]
                return "rbxassetid://5167344093";
            end;
            v131.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1300 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v131.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1301 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v131;
        end)()))
        p_u_3:add_dance_for_id(128, ((function() --[[ Line: 1304 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v132 = p_u_4.DanceInfoBase:new()
            v132.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1306 ]]
                return "Polaroid Shake";
            end;
            v132.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1307 ]]
                return "";
            end;
            v132.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1308 ]]
                return "rbxassetid://2993990307";
            end;
            v132.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1309 ]]
                return "rbxassetid://5167349152";
            end;
            v132.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1310 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v132.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1311 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v132;
        end)()))
        p_u_3:add_dance_for_id(129, ((function() --[[ Line: 1314 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v133 = p_u_4.DanceInfoBase:new()
            v133.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1316 ]]
                return "Windshield Wiper";
            end;
            v133.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1317 ]]
                return "";
            end;
            v133.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1318 ]]
                return "rbxassetid://2993990346";
            end;
            v133.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1319 ]]
                return "rbxassetid://5167363484";
            end;
            v133.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1320 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v133.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1321 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v133;
        end)()))
        p_u_3:add_dance_for_id(130, ((function() --[[ Line: 1324 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v134 = p_u_4.DanceInfoBase:new()
            v134.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1326 ]]
                return "Lucky Shuffle";
            end;
            v134.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1327 ]]
                return "";
            end;
            v134.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1328 ]]
                return "rbxassetid://2993990346";
            end;
            v134.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1329 ]]
                return "rbxassetid://5167373234";
            end;
            v134.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1330 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v134.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1331 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v134;
        end)()))
        p_u_3:add_dance_for_id(131, ((function() --[[ Line: 1334 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v135 = p_u_4.DanceInfoBase:new()
            v135.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1336 ]]
                return "Clap and Spin";
            end;
            v135.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1337 ]]
                return "";
            end;
            v135.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1338 ]]
                return "rbxassetid://2993990264";
            end;
            v135.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1339 ]]
                return "rbxassetid://5167376052";
            end;
            v135.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1340 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v135.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1341 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v135;
        end)()))
        p_u_3:add_dance_for_id(132, ((function() --[[ Line: 1344 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v136 = p_u_4.DanceInfoBase:new()
            v136.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1346 ]]
                return "A Standing Ovation";
            end;
            v136.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1347 ]]
                return "";
            end;
            v136.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1348 ]]
                return "rbxassetid://2993990385";
            end;
            v136.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1349 ]]
                return "rbxassetid://5167378356";
            end;
            v136.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1350 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v136.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1351 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v136;
        end)()))
        p_u_3:add_dance_for_id(133, ((function() --[[ Line: 1354 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v137 = p_u_4.DanceInfoBase:new()
            v137.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1356 ]]
                return "Shake it up!";
            end;
            v137.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1357 ]]
                return "";
            end;
            v137.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1358 ]]
                return "rbxassetid://2993990346";
            end;
            v137.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1359 ]]
                return "rbxassetid://5167381104";
            end;
            v137.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1360 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v137.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1361 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v137;
        end)()))
        p_u_3:add_dance_for_id(134, ((function() --[[ Line: 1364 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v138 = p_u_4.DanceInfoBase:new()
            v138.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1366 ]]
                return "Sick Diss";
            end;
            v138.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1367 ]]
                return "";
            end;
            v138.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1368 ]]
                return "rbxassetid://2993241780";
            end;
            v138.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1369 ]]
                return "rbxassetid://5167384488";
            end;
            v138.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1370 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v138.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1371 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v138;
        end)()))
        p_u_3:add_dance_for_id(135, ((function() --[[ Line: 1374 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v139 = p_u_4.DanceInfoBase:new()
            v139.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1376 ]]
                return "Spread the Love";
            end;
            v139.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1377 ]]
                return "";
            end;
            v139.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1378 ]]
                return "rbxassetid://2993990385";
            end;
            v139.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1379 ]]
                return "rbxassetid://5167386830";
            end;
            v139.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1380 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v139.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1381 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v139;
        end)()))
        p_u_3:add_dance_for_id(136, ((function() --[[ Line: 1384 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v140 = p_u_4.DanceInfoBase:new()
            v140.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1386 ]]
                return "TikTok Crazy";
            end;
            v140.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1387 ]]
                return "";
            end;
            v140.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1388 ]]
                return "rbxassetid://2993990427";
            end;
            v140.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1389 ]]
                return "rbxassetid://5167389049";
            end;
            v140.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1390 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v140.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1391 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v140;
        end)()))
        p_u_3:add_dance_for_id(137, ((function() --[[ Line: 1394 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v141 = p_u_4.DanceInfoBase:new()
            v141.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1396 ]]
                return "Oddly Satisfying";
            end;
            v141.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1397 ]]
                return "";
            end;
            v141.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1398 ]]
                return "rbxassetid://2993241780";
            end;
            v141.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1399 ]]
                return "rbxassetid://5167391327";
            end;
            v141.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1400 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v141.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1401 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v141;
        end)()))
        p_u_3:add_dance_for_id(138, ((function() --[[ Line: 1404 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v142 = p_u_4.DanceInfoBase:new()
            v142.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1406 ]]
                return "Die Schadenfreude";
            end;
            v142.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1407 ]]
                return "";
            end;
            v142.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1408 ]]
                return "rbxassetid://2993990346";
            end;
            v142.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1409 ]]
                return "rbxassetid://5167393332";
            end;
            v142.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1410 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v142.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1411 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v142;
        end)()))
        p_u_3:add_dance_for_id(139, ((function() --[[ Line: 1414 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v143 = p_u_4.DanceInfoBase:new()
            v143.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1416 ]]
                return "Mad Fire";
            end;
            v143.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1417 ]]
                return "";
            end;
            v143.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1418 ]]
                return "rbxassetid://2993241780";
            end;
            v143.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1419 ]]
                return "rbxassetid://5167400263";
            end;
            v143.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1420 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v143.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1421 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v143;
        end)()))
        p_u_3:add_dance_for_id(140, ((function() --[[ Line: 1424 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v144 = p_u_4.DanceInfoBase:new()
            v144.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1426 ]]
                return "Thrilling!";
            end;
            v144.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1427 ]]
                return "";
            end;
            v144.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1428 ]]
                return "rbxassetid://2993241780";
            end;
            v144.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1429 ]]
                return "rbxassetid://5167402389";
            end;
            v144.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1430 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v144.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1431 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v144;
        end)()))
        p_u_3:add_dance_for_id(141, ((function() --[[ Line: 1434 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v145 = p_u_4.DanceInfoBase:new()
            v145.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1436 ]]
                return "TikTok Timebomb";
            end;
            v145.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1437 ]]
                return "";
            end;
            v145.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1438 ]]
                return "rbxassetid://2993990346";
            end;
            v145.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1439 ]]
                return "rbxassetid://5167404777";
            end;
            v145.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1440 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v145.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1441 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v145;
        end)()))
        p_u_3:add_dance_for_id(142, ((function() --[[ Line: 1444 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v146 = p_u_4.DanceInfoBase:new()
            v146.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1446 ]]
                return "Can\'t Touch This!";
            end;
            v146.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1447 ]]
                return "";
            end;
            v146.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1448 ]]
                return "rbxassetid://2993990346";
            end;
            v146.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1449 ]]
                return "rbxassetid://5167412633";
            end;
            v146.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1450 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v146.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1451 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v146;
        end)()))
        p_u_3:add_dance_for_id(143, ((function() --[[ Line: 1454 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v147 = p_u_4.DanceInfoBase:new()
            v147.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1456 ]]
                return "Five Dollar";
            end;
            v147.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1457 ]]
                return "";
            end;
            v147.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1458 ]]
                return "rbxassetid://2993990264";
            end;
            v147.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1459 ]]
                return "rbxassetid://5167414314";
            end;
            v147.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1460 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v147.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1461 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v147;
        end)()))
        p_u_3:add_dance_for_id(144, ((function() --[[ Line: 1464 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v148 = p_u_4.DanceInfoBase:new()
            v148.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1466 ]]
                return "Where You At";
            end;
            v148.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1467 ]]
                return "";
            end;
            v148.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1468 ]]
                return "rbxassetid://2993990385";
            end;
            v148.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1469 ]]
                return "rbxassetid://5167416595";
            end;
            v148.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1470 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v148.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1471 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v148;
        end)()))
        p_u_3:add_dance_for_id(145, ((function() --[[ Line: 1474 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v149 = p_u_4.DanceInfoBase:new()
            v149.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1476 ]]
                return "The Happy Clappy Dance";
            end;
            v149.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1477 ]]
                return "";
            end;
            v149.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1478 ]]
                return "rbxassetid://2993241780";
            end;
            v149.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1479 ]]
                return "rbxassetid://5167429876";
            end;
            v149.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1480 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v149.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1481 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v149;
        end)()))
        p_u_3:add_dance_for_id(146, ((function() --[[ Line: 1484 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v150 = p_u_4.DanceInfoBase:new()
            v150.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1486 ]]
                return "Cower";
            end;
            v150.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1487 ]]
                return "";
            end;
            v150.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1488 ]]
                return "rbxassetid://2993241780";
            end;
            v150.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1489 ]]
                return "rbxassetid://4940563117";
            end;
            v150.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1490 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v150.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1491 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v150;
        end)()))
        p_u_3:add_dance_for_id(147, ((function() --[[ Line: 1494 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v151 = p_u_4.DanceInfoBase:new()
            v151.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1496 ]]
                return "Much Confuse";
            end;
            v151.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1497 ]]
                return "";
            end;
            v151.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1498 ]]
                return "rbxassetid://2993241780";
            end;
            v151.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1499 ]]
                return "rbxassetid://4940561610";
            end;
            v151.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1500 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v151.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1501 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v151;
        end)()))
        p_u_3:add_dance_for_id(148, ((function() --[[ Line: 1504 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v152 = p_u_4.DanceInfoBase:new()
            v152.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1506 ]]
                return "Downtown";
            end;
            v152.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1507 ]]
                return "";
            end;
            v152.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1508 ]]
                return "rbxassetid://2993990346";
            end;
            v152.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1509 ]]
                return "rbxassetid://5167319226";
            end;
            v152.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1510 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v152.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1511 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v152;
        end)()))
        p_u_3:add_dance_for_id(149, ((function() --[[ Line: 1514 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v153 = p_u_4.DanceInfoBase:new()
            v153.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1516 ]]
                return "Best Mates";
            end;
            v153.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1517 ]]
                return "";
            end;
            v153.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1518 ]]
                return "rbxassetid://2993241780";
            end;
            v153.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1519 ]]
                return "rbxassetid://5167773613";
            end;
            v153.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1520 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v153.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1521 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v153;
        end)()))
        p_u_3:add_dance_for_id(150, ((function() --[[ Line: 1524 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v154 = p_u_4.DanceInfoBase:new()
            v154.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1526 ]]
                return "Dab!";
            end;
            v154.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1527 ]]
                return "";
            end;
            v154.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1528 ]]
                return "rbxassetid://2993241780";
            end;
            v154.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1529 ]]
                return "rbxassetid://5167774741";
            end;
            v154.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1530 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v154.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1531 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v154;
        end)()))
        p_u_3:add_dance_for_id(151, ((function() --[[ Line: 1534 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v155 = p_u_4.DanceInfoBase:new()
            v155.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1536 ]]
                return "Wiggle Wiggle Wiggle";
            end;
            v155.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1537 ]]
                return "";
            end;
            v155.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1538 ]]
                return "rbxassetid://2993241780";
            end;
            v155.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1539 ]]
                return "rbxassetid://5167775879";
            end;
            v155.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1540 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v155.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1541 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v155;
        end)()))
        p_u_3:add_dance_for_id(152, ((function() --[[ Line: 1544 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v156 = p_u_4.DanceInfoBase:new()
            v156.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1546 ]]
                return "Dance Moves";
            end;
            v156.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1547 ]]
                return "";
            end;
            v156.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1548 ]]
                return "rbxassetid://2993241780";
            end;
            v156.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1549 ]]
                return "rbxassetid://5167781108";
            end;
            v156.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1550 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v156.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1551 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v156;
        end)()))
        p_u_3:add_dance_for_id(153, ((function() --[[ Line: 1556 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v157 = p_u_4.DanceInfoBase:new()
            v157.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1558 ]]
                return "Macarena";
            end;
            v157.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1559 ]]
                return "";
            end;
            v157.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1560 ]]
                return "rbxassetid://2993990346";
            end;
            v157.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1561 ]]
                return "rbxassetid://5212176673";
            end;
            v157.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1562 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v157.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1563 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v157;
        end)()))
        p_u_3:add_dance_for_id(154, ((function() --[[ Line: 1566 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v158 = p_u_4.DanceInfoBase:new()
            v158.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1568 ]]
                return "I\'m Jello!";
            end;
            v158.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1569 ]]
                return "";
            end;
            v158.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1570 ]]
                return "rbxassetid://2993990307";
            end;
            v158.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1571 ]]
                return "rbxassetid://5212178203";
            end;
            v158.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1572 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v158.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1573 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v158;
        end)()))
        p_u_3:add_dance_for_id(155, ((function() --[[ Line: 1576 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v159 = p_u_4.DanceInfoBase:new()
            v159.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1578 ]]
                return "Breakstep Warmup";
            end;
            v159.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1579 ]]
                return "";
            end;
            v159.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1580 ]]
                return "rbxassetid://2993241780";
            end;
            v159.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1581 ]]
                return "rbxassetid://5212179681";
            end;
            v159.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1582 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v159.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1583 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v159;
        end)()))
        p_u_3:add_dance_for_id(156, ((function() --[[ Line: 1586 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v160 = p_u_4.DanceInfoBase:new()
            v160.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1588 ]]
                return "Arabesque";
            end;
            v160.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1589 ]]
                return "";
            end;
            v160.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1590 ]]
                return "rbxassetid://2993241780";
            end;
            v160.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1591 ]]
                return "rbxassetid://5212181070";
            end;
            v160.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1592 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v160.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1593 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v160;
        end)()))
        p_u_3:add_dance_for_id(157, ((function() --[[ Line: 1596 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v161 = p_u_4.DanceInfoBase:new()
            v161.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1598 ]]
                return "Happy Street";
            end;
            v161.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1599 ]]
                return "";
            end;
            v161.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1600 ]]
                return "rbxassetid://2993241780";
            end;
            v161.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1601 ]]
                return "rbxassetid://5212184402";
            end;
            v161.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1602 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v161.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1603 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v161;
        end)()))
        p_u_3:add_dance_for_id(158, ((function() --[[ Line: 1606 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v162 = p_u_4.DanceInfoBase:new()
            v162.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1608 ]]
                return "Club Penguin";
            end;
            v162.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1609 ]]
                return "";
            end;
            v162.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1610 ]]
                return "rbxassetid://2993241780";
            end;
            v162.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1611 ]]
                return "rbxassetid://5303556410";
            end;
            v162.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1612 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v162.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1613 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v162;
        end)()))
        p_u_3:add_dance_for_id(159, ((function() --[[ Line: 1616 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v163 = p_u_4.DanceInfoBase:new()
            v163.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1618 ]]
                return "Pumpernickel";
            end;
            v163.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1619 ]]
                return "";
            end;
            v163.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1620 ]]
                return "rbxassetid://2993241780";
            end;
            v163.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1621 ]]
                return "rbxassetid://5394354538";
            end;
            v163.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1622 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v163.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1623 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v163;
        end)()))
        p_u_3:add_dance_for_id(160, ((function() --[[ Line: 1626 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v164 = p_u_4.DanceInfoBase:new()
            v164.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1628 ]]
                return "Godlike";
            end;
            v164.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1629 ]]
                return "";
            end;
            v164.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1630 ]]
                return "rbxassetid://2993241780";
            end;
            v164.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1631 ]]
                return "rbxassetid://5479367401";
            end;
            v164.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1632 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v164.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1633 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v164;
        end)()))
        p_u_3:add_dance_for_id(161, ((function() --[[ Line: 1636 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v165 = p_u_4.DanceInfoBase:new()
            v165.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1638 ]]
                return "Katzosky Kick";
            end;
            v165.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1639 ]]
                return "";
            end;
            v165.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1640 ]]
                return "rbxassetid://2993241780";
            end;
            v165.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1641 ]]
                return "rbxassetid://5592866369";
            end;
            v165.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1642 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v165.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1643 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v165;
        end)()))
        p_u_3:add_dance_for_id(162, ((function() --[[ Line: 1646 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v166 = p_u_4.DanceInfoBase:new()
            v166.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1648 ]]
                return "Woah Woah Woah!";
            end;
            v166.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1649 ]]
                return "";
            end;
            v166.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1650 ]]
                return "rbxassetid://2993241780";
            end;
            v166.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1651 ]]
                return "rbxassetid://5608264104";
            end;
            v166.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1652 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v166.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1653 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v166;
        end)()))
        p_u_3:add_dance_for_id(163, ((function() --[[ Line: 1656 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v167 = p_u_4.DanceInfoBase:new()
            v167.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1658 ]]
                return "LAGGGGGG";
            end;
            v167.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1659 ]]
                return "";
            end;
            v167.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1660 ]]
                return "rbxassetid://2993990385";
            end;
            v167.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1661 ]]
                return "rbxassetid://5682131931";
            end;
            v167.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1662 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v167.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1663 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v167;
        end)()))
        p_u_3:add_dance_for_id(164, ((function() --[[ Line: 1666 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v168 = p_u_4.DanceInfoBase:new()
            v168.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1668 ]]
                return "It\'s Time!";
            end;
            v168.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1669 ]]
                return "";
            end;
            v168.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1670 ]]
                return "rbxassetid://2993990346";
            end;
            v168.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1671 ]]
                return "rbxassetid://5682133861";
            end;
            v168.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1672 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v168.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1673 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v168;
        end)()))
        p_u_3:add_dance_for_id(165, ((function() --[[ Line: 1676 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v169 = p_u_4.DanceInfoBase:new()
            v169.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1678 ]]
                return "Suddenly Sad";
            end;
            v169.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1679 ]]
                return "";
            end;
            v169.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1680 ]]
                return "rbxassetid://2993241780";
            end;
            v169.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1681 ]]
                return "rbxassetid://5682143082";
            end;
            v169.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1682 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v169.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1683 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v169;
        end)()))
        p_u_3:add_dance_for_id(166, ((function() --[[ Line: 1686 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v170 = p_u_4.DanceInfoBase:new()
            v170.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1688 ]]
                return "Porch Side";
            end;
            v170.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1689 ]]
                return "";
            end;
            v170.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1690 ]]
                return "rbxassetid://2993241780";
            end;
            v170.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1691 ]]
                return "rbxassetid://5682144416";
            end;
            v170.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1692 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v170.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1693 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v170;
        end)()))
        p_u_3:add_dance_for_id(167, ((function() --[[ Line: 1696 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v171 = p_u_4.DanceInfoBase:new()
            v171.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1698 ]]
                return "Diversion";
            end;
            v171.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1699 ]]
                return "";
            end;
            v171.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1700 ]]
                return "rbxassetid://2993990264";
            end;
            v171.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1701 ]]
                return "rbxassetid://5682145431";
            end;
            v171.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1702 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v171.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1703 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v171;
        end)()))
        p_u_3:add_dance_for_id(168, ((function() --[[ Line: 1706 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v172 = p_u_4.DanceInfoBase:new()
            v172.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1708 ]]
                return "Beaned!";
            end;
            v172.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1709 ]]
                return "";
            end;
            v172.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1710 ]]
                return "rbxassetid://2993990385";
            end;
            v172.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1711 ]]
                return "rbxassetid://5682146993";
            end;
            v172.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1712 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v172.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1713 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v172;
        end)()))
        p_u_3:add_dance_for_id(169, ((function() --[[ Line: 1716 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v173 = p_u_4.DanceInfoBase:new()
            v173.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1718 ]]
                return "Backflip Fail!";
            end;
            v173.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1719 ]]
                return "";
            end;
            v173.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1720 ]]
                return "rbxassetid://2993990427";
            end;
            v173.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1721 ]]
                return "rbxassetid://5682155846";
            end;
            v173.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1722 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v173.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1723 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v173;
        end)()))
        p_u_3:add_dance_for_id(170, ((function() --[[ Line: 1726 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v174 = p_u_4.DanceInfoBase:new()
            v174.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1728 ]]
                return "Heads Will Roll";
            end;
            v174.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1729 ]]
                return "";
            end;
            v174.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1730 ]]
                return "rbxassetid://2993241780";
            end;
            v174.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1731 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v174.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1732 ]]
                return "rbxassetid://5813442821";
            end;
            v174.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1733 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v174;
        end)()))
        p_u_3:add_dance_for_id(171, ((function() --[[ Line: 1736 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v175 = p_u_4.DanceInfoBase:new()
            v175.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1738 ]]
                return "Literally Just Dead";
            end;
            v175.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1739 ]]
                return "";
            end;
            v175.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1740 ]]
                return "rbxassetid://2993241780";
            end;
            v175.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1741 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v175.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1742 ]]
                return "rbxassetid://5841818449";
            end;
            v175.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1743 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v175;
        end)()))
        p_u_3:add_dance_for_id(172, ((function() --[[ Line: 1746 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v176 = p_u_4.DanceInfoBase:new()
            v176.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1748 ]]
                return "Get Real";
            end;
            v176.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1749 ]]
                return "";
            end;
            v176.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1750 ]]
                return "rbxassetid://2993241780";
            end;
            v176.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1751 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v176.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1752 ]]
                return "rbxassetid://5909554967";
            end;
            v176.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1753 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v176;
        end)()))
        p_u_3:add_dance_for_id(173, ((function() --[[ Line: 1756 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v177 = p_u_4.DanceInfoBase:new()
            v177.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1758 ]]
                return "Toy Soldier";
            end;
            v177.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1759 ]]
                return "";
            end;
            v177.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1760 ]]
                return "rbxassetid://2993241780";
            end;
            v177.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1761 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v177.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1762 ]]
                return "rbxassetid://6034008184";
            end;
            v177.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1763 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v177;
        end)()))
        p_u_3:add_dance_for_id(174, ((function() --[[ Line: 1766 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v178 = p_u_4.DanceInfoBase:new()
            v178.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1768 ]]
                return "Super Springy";
            end;
            v178.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1769 ]]
                return "";
            end;
            v178.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1770 ]]
                return "rbxassetid://2993241780";
            end;
            v178.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1771 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v178.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1772 ]]
                return "rbxassetid://6186876018";
            end;
            v178.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1773 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v178;
        end)()))
        p_u_3:add_dance_for_id(175, ((function() --[[ Line: 1776 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v179 = p_u_4.DanceInfoBase:new()
            v179.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1778 ]]
                return "The Eagle";
            end;
            v179.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1779 ]]
                return "";
            end;
            v179.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1780 ]]
                return "rbxassetid://2993990346";
            end;
            v179.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1781 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v179.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1782 ]]
                return "rbxassetid://6111993466";
            end;
            v179.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1783 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v179;
        end)()))
        p_u_3:add_dance_for_id(176, ((function() --[[ Line: 1786 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v180 = p_u_4.DanceInfoBase:new()
            v180.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1788 ]]
                return "A Real BANGER!";
            end;
            v180.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1789 ]]
                return "";
            end;
            v180.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1790 ]]
                return "rbxassetid://2993990385";
            end;
            v180.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1791 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v180.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1792 ]]
                return "rbxassetid://12646811239";
            end;
            v180.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1793 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v180;
        end)()))
        p_u_3:add_dance_for_id(177, ((function() --[[ Line: 1796 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v181 = p_u_4.DanceInfoBase:new()
            v181.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1798 ]]
                return "Pelo MOVES";
            end;
            v181.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1799 ]]
                return "";
            end;
            v181.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1800 ]]
                return "rbxassetid://2993990427";
            end;
            v181.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1801 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v181.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1802 ]]
                return "rbxassetid://6197558816";
            end;
            v181.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1803 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v181;
        end)()))
        p_u_3:add_dance_for_id(178, ((function() --[[ Line: 1806 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v182 = p_u_4.DanceInfoBase:new()
            v182.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1808 ]]
                return "Smooth Sailing";
            end;
            v182.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1809 ]]
                return "";
            end;
            v182.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1810 ]]
                return "rbxassetid://2993241780";
            end;
            v182.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1811 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v182.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1812 ]]
                return "rbxassetid://6377262209";
            end;
            v182.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1813 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v182;
        end)()))
        p_u_3:add_dance_for_id(179, ((function() --[[ Line: 1816 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v183 = p_u_4.DanceInfoBase:new()
            v183.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1818 ]]
                return "A New You!";
            end;
            v183.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1819 ]]
                return "";
            end;
            v183.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1820 ]]
                return "rbxassetid://2993241780";
            end;
            v183.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1821 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v183.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1822 ]]
                return "rbxassetid://6399401447";
            end;
            v183.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1823 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v183;
        end)()))
        p_u_3:add_dance_for_id(180, ((function() --[[ Line: 1826 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v184 = p_u_4.DanceInfoBase:new()
            v184.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1828 ]]
                return "Food Delivery";
            end;
            v184.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1829 ]]
                return "";
            end;
            v184.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1830 ]]
                return "rbxassetid://2993241780";
            end;
            v184.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1831 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v184.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1832 ]]
                return "rbxassetid://6433512230";
            end;
            v184.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1833 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v184;
        end)()))
        p_u_3:add_dance_for_id(181, ((function() --[[ Line: 1836 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v185 = p_u_4.DanceInfoBase:new()
            v185.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1838 ]]
                return "The Worm";
            end;
            v185.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1839 ]]
                return "";
            end;
            v185.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1840 ]]
                return "rbxassetid://2993990385";
            end;
            v185.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1841 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Rare;
            end;
            v185.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1842 ]]
                return "rbxassetid://6433529279";
            end;
            v185.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1843 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v185;
        end)()))
        p_u_3:add_dance_for_id(182, ((function() --[[ Line: 1846 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v186 = p_u_4.DanceInfoBase:new()
            v186.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1848 ]]
                return "The Boston Break Dance";
            end;
            v186.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1849 ]]
                return "";
            end;
            v186.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1850 ]]
                return "rbxassetid://2993990427";
            end;
            v186.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1851 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v186.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1852 ]]
                return "rbxassetid://6480751875";
            end;
            v186.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1853 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v186;
        end)()))
        p_u_3:add_dance_for_id(183, ((function() --[[ Line: 1856 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v187 = p_u_4.DanceInfoBase:new()
            v187.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1858 ]]
                return "Shattered!";
            end;
            v187.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1859 ]]
                return "";
            end;
            v187.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1860 ]]
                return "rbxassetid://2993241780";
            end;
            v187.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1861 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v187.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1862 ]]
                return "rbxassetid://6737685682";
            end;
            v187.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1863 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v187;
        end)()))
        p_u_3:add_dance_for_id(184, ((function() --[[ Line: 1866 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v188 = p_u_4.DanceInfoBase:new()
            v188.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1868 ]]
                return "Invisible Fishing";
            end;
            v188.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1869 ]]
                return "";
            end;
            v188.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1870 ]]
                return "rbxassetid://2993241780";
            end;
            v188.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1871 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v188.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1872 ]]
                return "rbxassetid://7098205367";
            end;
            v188.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1873 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v188;
        end)()))
        p_u_3:add_dance_for_id(185, ((function() --[[ Line: 1876 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v189 = p_u_4.DanceInfoBase:new()
            v189.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1878 ]]
                return "Ballin\'";
            end;
            v189.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1879 ]]
                return "";
            end;
            v189.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1880 ]]
                return "rbxassetid://2993241780";
            end;
            v189.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1881 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v189.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1882 ]]
                return "rbxassetid://7098206780";
            end;
            v189.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1883 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v189;
        end)()))
        p_u_3:add_dance_for_id(186, ((function() --[[ Line: 1886 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v190 = p_u_4.DanceInfoBase:new()
            v190.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1888 ]]
                return "Ragdoll";
            end;
            v190.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1889 ]]
                return "";
            end;
            v190.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1890 ]]
                return "rbxassetid://2993241780";
            end;
            v190.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1891 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v190.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1892 ]]
                return "rbxassetid://7218363696";
            end;
            v190.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1893 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v190;
        end)()))
        p_u_3:add_dance_for_id(187, ((function() --[[ Line: 1896 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v191 = p_u_4.DanceInfoBase:new()
            v191.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1898 ]]
                return "16-bit Shuffle";
            end;
            v191.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1899 ]]
                return "";
            end;
            v191.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1900 ]]
                return "rbxassetid://2993241780";
            end;
            v191.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1901 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v191.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1902 ]]
                return "rbxassetid://7652636912";
            end;
            v191.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1903 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v191;
        end)()))
        p_u_3:add_dance_for_id(188, ((function() --[[ Line: 1906 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v192 = p_u_4.DanceInfoBase:new()
            v192.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1908 ]]
                return "Ski-Ba-Bop";
            end;
            v192.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1909 ]]
                return "";
            end;
            v192.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1910 ]]
                return "rbxassetid://2993241780";
            end;
            v192.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1911 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v192.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1912 ]]
                return "rbxassetid://7652640058";
            end;
            v192.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1913 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v192;
        end)()))
        p_u_3:add_dance_for_id(189, ((function() --[[ Line: 1916 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v193 = p_u_4.DanceInfoBase:new()
            v193.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1918 ]]
                return "Pose Barrage";
            end;
            v193.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1919 ]]
                return "";
            end;
            v193.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1920 ]]
                return "rbxassetid://2993241780";
            end;
            v193.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1921 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v193.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1922 ]]
                return "rbxassetid://7785073186";
            end;
            v193.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1923 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v193;
        end)()))
        p_u_3:add_dance_for_id(190, ((function() --[[ Line: 1926 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v194 = p_u_4.DanceInfoBase:new()
            v194.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1928 ]]
                return "Ryujin Dance";
            end;
            v194.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1929 ]]
                return "";
            end;
            v194.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1930 ]]
                return "rbxassetid://2993241780";
            end;
            v194.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1931 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Common;
            end;
            v194.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1932 ]]
                return "rbxassetid://7785086268";
            end;
            v194.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1933 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v194;
        end)()))
        p_u_3:add_dance_for_id(191, ((function() --[[ Line: 1936 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v195 = p_u_4.DanceInfoBase:new()
            v195.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1938 ]]
                return "Oh...";
            end;
            v195.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1939 ]]
                return "";
            end;
            v195.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1940 ]]
                return "rbxassetid://2993241780";
            end;
            v195.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1941 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v195.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1942 ]]
                return "rbxassetid://7834210313";
            end;
            v195.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1943 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v195;
        end)()))
        p_u_3:add_dance_for_id(192, ((function() --[[ Line: 1946 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v196 = p_u_4.DanceInfoBase:new()
            v196.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1948 ]]
                return "Fashionista Diva";
            end;
            v196.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1949 ]]
                return "";
            end;
            v196.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1950 ]]
                return "rbxassetid://2993241780";
            end;
            v196.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1951 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v196.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1952 ]]
                return "rbxassetid://7876618016";
            end;
            v196.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1953 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v196;
        end)()))
        p_u_3:add_dance_for_id(193, ((function() --[[ Line: 1956 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v197 = p_u_4.DanceInfoBase:new()
            v197.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1958 ]]
                return "Last Party Night";
            end;
            v197.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1959 ]]
                return "";
            end;
            v197.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1960 ]]
                return "rbxassetid://2993241780";
            end;
            v197.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1961 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v197.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1962 ]]
                return "rbxassetid://8021209686";
            end;
            v197.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1963 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v197;
        end)()))
        p_u_3:add_dance_for_id(194, ((function() --[[ Line: 1966 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v198 = p_u_4.DanceInfoBase:new()
            v198.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1968 ]]
                return "Mousou Mousou";
            end;
            v198.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1969 ]]
                return "";
            end;
            v198.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1970 ]]
                return "rbxassetid://2993241780";
            end;
            v198.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1971 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v198.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1972 ]]
                return "rbxassetid://8021223992";
            end;
            v198.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1973 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v198;
        end)()))
        p_u_3:add_dance_for_id(195, ((function() --[[ Line: 1976 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v199 = p_u_4.DanceInfoBase:new()
            v199.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1978 ]]
                return "Feelin\' GREAT";
            end;
            v199.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1979 ]]
                return "";
            end;
            v199.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1980 ]]
                return "rbxassetid://2993241780";
            end;
            v199.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1981 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v199.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1982 ]]
                return "rbxassetid://8076277257";
            end;
            v199.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1983 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v199;
        end)()))
        p_u_3:add_dance_for_id(196, ((function() --[[ Line: 1986 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v200 = p_u_4.DanceInfoBase:new()
            v200.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1988 ]]
                return "Fine China";
            end;
            v200.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1989 ]]
                return "";
            end;
            v200.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1990 ]]
                return "rbxassetid://2993241780";
            end;
            v200.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 1991 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v200.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 1992 ]]
                return "rbxassetid://8076281283";
            end;
            v200.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 1993 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v200;
        end)()))
        p_u_3:add_dance_for_id(197, ((function() --[[ Line: 1996 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v201 = p_u_4.DanceInfoBase:new()
            v201.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1998 ]]
                return "Sugar Dance";
            end;
            v201.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 1999 ]]
                return "";
            end;
            v201.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2000 ]]
                return "rbxassetid://2993241780";
            end;
            v201.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2001 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v201.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2002 ]]
                return "rbxassetid://8098043302";
            end;
            v201.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2003 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v201;
        end)()))
        p_u_3:add_dance_for_id(198, ((function() --[[ Line: 2006 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v202 = p_u_4.DanceInfoBase:new()
            v202.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2008 ]]
                return "Sayonara";
            end;
            v202.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2009 ]]
                return "";
            end;
            v202.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2010 ]]
                return "rbxassetid://2993241780";
            end;
            v202.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2011 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v202.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2012 ]]
                return "rbxassetid://8098049832";
            end;
            v202.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2013 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v202;
        end)()))
        p_u_3:add_dance_for_id(199, ((function() --[[ Line: 2016 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v203 = p_u_4.DanceInfoBase:new()
            v203.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2018 ]]
                return "The Ketchup Dance";
            end;
            v203.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2019 ]]
                return "";
            end;
            v203.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2020 ]]
                return "rbxassetid://2993990346";
            end;
            v203.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2021 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v203.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2022 ]]
                return "rbxassetid://8108615791";
            end;
            v203.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2023 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v203;
        end)()))
        p_u_3:add_dance_for_id(200, ((function() --[[ Line: 2026 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v204 = p_u_4.DanceInfoBase:new()
            v204.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2028 ]]
                return "Floppy Hands";
            end;
            v204.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2029 ]]
                return "";
            end;
            v204.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2030 ]]
                return "rbxassetid://2993990427";
            end;
            v204.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2031 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v204.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2032 ]]
                return "rbxassetid://8108772226";
            end;
            v204.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2033 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v204;
        end)()))
        p_u_3:add_dance_for_id(201, ((function() --[[ Line: 2036 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v205 = p_u_4.DanceInfoBase:new()
            v205.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2038 ]]
                return "Star Power!";
            end;
            v205.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2039 ]]
                return "";
            end;
            v205.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2040 ]]
                return "rbxassetid://2993990346";
            end;
            v205.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2041 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v205.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2042 ]]
                return "rbxassetid://8108775347";
            end;
            v205.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2043 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v205;
        end)()))
        p_u_3:add_dance_for_id(202, ((function() --[[ Line: 2046 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v206 = p_u_4.DanceInfoBase:new()
            v206.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2048 ]]
                return "To the MOON!";
            end;
            v206.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2049 ]]
                return "";
            end;
            v206.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2050 ]]
                return "rbxassetid://2993990385";
            end;
            v206.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2051 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v206.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2052 ]]
                return "rbxassetid://8145522287";
            end;
            v206.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2053 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v206;
        end)()))
        p_u_3:add_dance_for_id(203, ((function() --[[ Line: 2056 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v207 = p_u_4.DanceInfoBase:new()
            v207.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2058 ]]
                return "Stomp >:(";
            end;
            v207.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2059 ]]
                return "";
            end;
            v207.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2060 ]]
                return "rbxassetid://2993990427";
            end;
            v207.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2061 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v207.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2062 ]]
                return "rbxassetid://8145525409";
            end;
            v207.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2063 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v207;
        end)()))
        p_u_3:add_dance_for_id(204, ((function() --[[ Line: 2066 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v208 = p_u_4.DanceInfoBase:new()
            v208.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2068 ]]
                return "True Hearts";
            end;
            v208.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2069 ]]
                return "";
            end;
            v208.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2070 ]]
                return "rbxassetid://2993990307";
            end;
            v208.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2071 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v208.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2072 ]]
                return "rbxassetid://8145530282";
            end;
            v208.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2073 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v208;
        end)()))
        p_u_3:add_dance_for_id(205, ((function() --[[ Line: 2076 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v209 = p_u_4.DanceInfoBase:new()
            v209.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2078 ]]
                return "Surprise!!";
            end;
            v209.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2079 ]]
                return "";
            end;
            v209.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2080 ]]
                return "rbxassetid://2993990307";
            end;
            v209.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2081 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v209.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2082 ]]
                return "rbxassetid://8195397993";
            end;
            v209.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2083 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v209;
        end)()))
        p_u_3:add_dance_for_id(206, ((function() --[[ Line: 2086 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v210 = p_u_4.DanceInfoBase:new()
            v210.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2088 ]]
                return "Last Friday";
            end;
            v210.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2089 ]]
                return "";
            end;
            v210.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2090 ]]
                return "rbxassetid://2993241780";
            end;
            v210.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2091 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v210.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2092 ]]
                return "rbxassetid://8195399655";
            end;
            v210.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2093 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v210;
        end)()))
        p_u_3:add_dance_for_id(207, ((function() --[[ Line: 2096 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v211 = p_u_4.DanceInfoBase:new()
            v211.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2098 ]]
                return "Head.Anchored";
            end;
            v211.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2099 ]]
                return "";
            end;
            v211.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2100 ]]
                return "rbxassetid://2993990346";
            end;
            v211.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2101 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v211.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2102 ]]
                return "rbxassetid://8195401229";
            end;
            v211.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2103 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v211;
        end)()))
        p_u_3:add_dance_for_id(208, ((function() --[[ Line: 2106 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v212 = p_u_4.DanceInfoBase:new()
            v212.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2108 ]]
                return "Shakey";
            end;
            v212.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2109 ]]
                return "";
            end;
            v212.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2110 ]]
                return "rbxassetid://2993990427";
            end;
            v212.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2111 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v212.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2112 ]]
                return "rbxassetid://8195402976";
            end;
            v212.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2113 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v212;
        end)()))
        p_u_3:add_dance_for_id(209, ((function() --[[ Line: 2116 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v213 = p_u_4.DanceInfoBase:new()
            v213.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2118 ]]
                return "Irish Meadow Dance";
            end;
            v213.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2119 ]]
                return "";
            end;
            v213.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2120 ]]
                return "rbxassetid://2993241780";
            end;
            v213.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2121 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v213.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2122 ]]
                return "rbxassetid://8195405737";
            end;
            v213.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2123 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v213;
        end)()))
        p_u_3:add_dance_for_id(210, ((function() --[[ Line: 2126 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v214 = p_u_4.DanceInfoBase:new()
            v214.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2128 ]]
                return "Slick!";
            end;
            v214.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2129 ]]
                return "";
            end;
            v214.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2130 ]]
                return "rbxassetid://2993241780";
            end;
            v214.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2131 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v214.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2132 ]]
                return "rbxassetid://8542445770";
            end;
            v214.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2133 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v214;
        end)()))
        p_u_3:add_dance_for_id(211, ((function() --[[ Line: 2136 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v215 = p_u_4.DanceInfoBase:new()
            v215.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2138 ]]
                return "Oh NOOO!!!";
            end;
            v215.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2139 ]]
                return "";
            end;
            v215.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2140 ]]
                return "rbxassetid://2993990385";
            end;
            v215.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2141 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v215.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2142 ]]
                return "rbxassetid://8249192926";
            end;
            v215.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2143 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v215;
        end)()))
        p_u_3:add_dance_for_id(212, ((function() --[[ Line: 2146 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v216 = p_u_4.DanceInfoBase:new()
            v216.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2148 ]]
                return "Animal";
            end;
            v216.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2149 ]]
                return "";
            end;
            v216.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2150 ]]
                return "rbxassetid://2993990427";
            end;
            v216.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2151 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v216.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2152 ]]
                return "rbxassetid://8249195090";
            end;
            v216.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2153 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v216;
        end)()))
        p_u_3:add_dance_for_id(213, ((function() --[[ Line: 2156 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v217 = p_u_4.DanceInfoBase:new()
            v217.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2158 ]]
                return "Easily Frightened";
            end;
            v217.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2159 ]]
                return "";
            end;
            v217.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2160 ]]
                return "rbxassetid://2993990307";
            end;
            v217.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2161 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v217.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2162 ]]
                return "rbxassetid://8249196320";
            end;
            v217.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2163 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v217;
        end)()))
        p_u_3:add_dance_for_id(214, ((function() --[[ Line: 2166 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v218 = p_u_4.DanceInfoBase:new()
            v218.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2168 ]]
                return "Electro Flow";
            end;
            v218.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2169 ]]
                return "";
            end;
            v218.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2170 ]]
                return "rbxassetid://2993241780";
            end;
            v218.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2171 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v218.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2172 ]]
                return "rbxassetid://8249198244";
            end;
            v218.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2173 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v218;
        end)()))
        p_u_3:add_dance_for_id(215, ((function() --[[ Line: 2176 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v219 = p_u_4.DanceInfoBase:new()
            v219.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2178 ]]
                return "Frightfully Funky";
            end;
            v219.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2179 ]]
                return "";
            end;
            v219.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2180 ]]
                return "rbxassetid://2993241780";
            end;
            v219.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2181 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v219.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2182 ]]
                return "rbxassetid://8291877059";
            end;
            v219.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2183 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v219;
        end)()))
        p_u_3:add_dance_for_id(216, ((function() --[[ Line: 2186 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v220 = p_u_4.DanceInfoBase:new()
            v220.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2188 ]]
                return "Off Balance";
            end;
            v220.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2189 ]]
                return "";
            end;
            v220.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2190 ]]
                return "rbxassetid://2993990385";
            end;
            v220.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2191 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v220.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2192 ]]
                return "rbxassetid://8291880727";
            end;
            v220.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2193 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v220;
        end)()))
        p_u_3:add_dance_for_id(217, ((function() --[[ Line: 2196 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v221 = p_u_4.DanceInfoBase:new()
            v221.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2198 ]]
                return "Leapin\' Lizards!";
            end;
            v221.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2199 ]]
                return "";
            end;
            v221.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2200 ]]
                return "rbxassetid://2993990346";
            end;
            v221.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2201 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v221.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2202 ]]
                return "rbxassetid://8368779835";
            end;
            v221.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2203 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v221;
        end)()))
        p_u_3:add_dance_for_id(218, ((function() --[[ Line: 2206 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v222 = p_u_4.DanceInfoBase:new()
            v222.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2208 ]]
                return "Knocked Down";
            end;
            v222.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2209 ]]
                return "";
            end;
            v222.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2210 ]]
                return "rbxassetid://2993990307";
            end;
            v222.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2211 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v222.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2212 ]]
                return "rbxassetid://8368782595";
            end;
            v222.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2213 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v222;
        end)()))
        p_u_3:add_dance_for_id(219, ((function() --[[ Line: 2216 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v223 = p_u_4.DanceInfoBase:new()
            v223.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2218 ]]
                return "Work it Out";
            end;
            v223.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2219 ]]
                return "";
            end;
            v223.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2220 ]]
                return "rbxassetid://2993241780";
            end;
            v223.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2221 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v223.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2222 ]]
                return "rbxassetid://8368787324";
            end;
            v223.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2223 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v223;
        end)()))
        p_u_3:add_dance_for_id(220, ((function() --[[ Line: 2226 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v224 = p_u_4.DanceInfoBase:new()
            v224.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2228 ]]
                return "Fever Time";
            end;
            v224.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2229 ]]
                return "";
            end;
            v224.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2230 ]]
                return "rbxassetid://2993990427";
            end;
            v224.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2231 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v224.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2232 ]]
                return "rbxassetid://8542468614";
            end;
            v224.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2233 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v224;
        end)()))
        p_u_3:add_dance_for_id(221, ((function() --[[ Line: 2236 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v225 = p_u_4.DanceInfoBase:new()
            v225.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2238 ]]
                return "I Could Fly";
            end;
            v225.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2239 ]]
                return "";
            end;
            v225.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2240 ]]
                return "rbxassetid://2993990385";
            end;
            v225.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2241 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v225.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2242 ]]
                return "rbxassetid://8542479472";
            end;
            v225.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2243 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v225;
        end)()))
        p_u_3:add_dance_for_id(222, ((function() --[[ Line: 2246 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v226 = p_u_4.DanceInfoBase:new()
            v226.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2248 ]]
                return "Baile Flamenco";
            end;
            v226.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2249 ]]
                return "";
            end;
            v226.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2250 ]]
                return "rbxassetid://2993241780";
            end;
            v226.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2251 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v226.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2252 ]]
                return "rbxassetid://8542485627";
            end;
            v226.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2253 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v226;
        end)()))
        p_u_3:add_dance_for_id(223, ((function() --[[ Line: 2256 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v227 = p_u_4.DanceInfoBase:new()
            v227.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2258 ]]
                return "Give You Up";
            end;
            v227.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2259 ]]
                return "";
            end;
            v227.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2260 ]]
                return "rbxassetid://2993241780";
            end;
            v227.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2261 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v227.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2262 ]]
                return "rbxassetid://8542493242";
            end;
            v227.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2263 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v227;
        end)()))
        p_u_3:add_dance_for_id(224, ((function() --[[ Line: 2266 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v228 = p_u_4.DanceInfoBase:new()
            v228.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2268 ]]
                return "Boogie Time";
            end;
            v228.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2269 ]]
                return "";
            end;
            v228.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2270 ]]
                return "rbxassetid://2993241780";
            end;
            v228.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2271 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v228.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2272 ]]
                return "rbxassetid://8542512799";
            end;
            v228.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2273 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v228;
        end)()))
        p_u_3:add_dance_for_id(225, ((function() --[[ Line: 2276 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v229 = p_u_4.DanceInfoBase:new()
            v229.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2278 ]]
                return "Reanimated";
            end;
            v229.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2279 ]]
                return "";
            end;
            v229.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2280 ]]
                return "rbxassetid://2993990427";
            end;
            v229.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2281 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v229.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2282 ]]
                return "rbxassetid://11508928615";
            end;
            v229.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2283 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v229;
        end)()))
        p_u_3:add_dance_for_id(226, ((function() --[[ Line: 2286 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v230 = p_u_4.DanceInfoBase:new()
            v230.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2288 ]]
                return "Loud & Proud";
            end;
            v230.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2289 ]]
                return "";
            end;
            v230.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2290 ]]
                return "rbxassetid://2993990385";
            end;
            v230.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2291 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v230.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2292 ]]
                return "rbxassetid://8698456791";
            end;
            v230.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2293 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v230;
        end)()))
        p_u_3:add_dance_for_id(227, ((function() --[[ Line: 2296 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v231 = p_u_4.DanceInfoBase:new()
            v231.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2298 ]]
                return "Smooth Moves";
            end;
            v231.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2299 ]]
                return "";
            end;
            v231.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2300 ]]
                return "rbxassetid://2993990346";
            end;
            v231.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2301 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v231.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2302 ]]
                return "rbxassetid://8698474623";
            end;
            v231.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2303 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v231;
        end)()))
        p_u_3:add_dance_for_id(228, ((function() --[[ Line: 2306 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v232 = p_u_4.DanceInfoBase:new()
            v232.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2308 ]]
                return "Error=True;";
            end;
            v232.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2309 ]]
                return "";
            end;
            v232.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2310 ]]
                return "rbxassetid://2993990307";
            end;
            v232.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2311 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v232.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2312 ]]
                return "rbxassetid://8699097976";
            end;
            v232.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2313 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.OnMiss;
            end;
            return v232;
        end)()))
        p_u_3:add_dance_for_id(229, ((function() --[[ Line: 2316 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v233 = p_u_4.DanceInfoBase:new()
            v233.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2318 ]]
                return "Suge (Yea Yea)";
            end;
            v233.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2319 ]]
                return "";
            end;
            v233.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2320 ]]
                return "rbxassetid://2993990346";
            end;
            v233.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2321 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v233.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2322 ]]
                return "rbxassetid://8949229000";
            end;
            v233.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2323 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v233;
        end)()))
        p_u_3:add_dance_for_id(230, ((function() --[[ Line: 2326 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v234 = p_u_4.DanceInfoBase:new()
            v234.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2328 ]]
                return "Crabby";
            end;
            v234.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2329 ]]
                return "";
            end;
            v234.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2330 ]]
                return "rbxassetid://2993990346";
            end;
            v234.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2331 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v234.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2332 ]]
                return "rbxassetid://9690244546";
            end;
            v234.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2333 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v234;
        end)()))
        p_u_3:add_dance_for_id(231, ((function() --[[ Line: 2336 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v235 = p_u_4.DanceInfoBase:new()
            v235.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2338 ]]
                return "Battlemage";
            end;
            v235.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2339 ]]
                return "";
            end;
            v235.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2340 ]]
                return "rbxassetid://2993990385";
            end;
            v235.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2341 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v235.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2342 ]]
                return "rbxassetid://9690241292";
            end;
            v235.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2343 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v235;
        end)()))
        p_u_3:add_dance_for_id(232, ((function() --[[ Line: 2346 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v236 = p_u_4.DanceInfoBase:new()
            v236.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2348 ]]
                return "Superstar HOP";
            end;
            v236.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2349 ]]
                return "";
            end;
            v236.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2350 ]]
                return "rbxassetid://2993990427";
            end;
            v236.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2351 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v236.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2352 ]]
                return "rbxassetid://9690269660";
            end;
            v236.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2353 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v236;
        end)()))
        p_u_3:add_dance_for_id(233, ((function() --[[ Line: 2356 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v237 = p_u_4.DanceInfoBase:new()
            v237.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2358 ]]
                return "Reconstruction";
            end;
            v237.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2359 ]]
                return "";
            end;
            v237.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2360 ]]
                return "rbxassetid://2993990385";
            end;
            v237.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2361 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v237.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2362 ]]
                return "rbxassetid://10540218559";
            end;
            v237.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2363 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v237;
        end)()))
        p_u_3:add_dance_for_id(234, ((function() --[[ Line: 2366 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v238 = p_u_4.DanceInfoBase:new()
            v238.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2368 ]]
                return "Samba de Janeiro";
            end;
            v238.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2369 ]]
                return "";
            end;
            v238.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2370 ]]
                return "rbxassetid://2993990346";
            end;
            v238.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2371 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v238.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2372 ]]
                return "rbxassetid://16630394363";
            end;
            v238.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2373 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v238;
        end)()))
        p_u_3:add_dance_for_id(235, ((function() --[[ Line: 2377 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v239 = p_u_4.DanceInfoBase:new()
            v239.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2379 ]]
                return "Boneless";
            end;
            v239.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2380 ]]
                return "";
            end;
            v239.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2381 ]]
                return "rbxassetid://2993990307";
            end;
            v239.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2382 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v239.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2383 ]]
                return "rbxassetid://11508934924";
            end;
            v239.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2384 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v239;
        end)()))
        p_u_3:add_dance_for_id(236, ((function() --[[ Line: 2387 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v240 = p_u_4.DanceInfoBase:new()
            v240.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2389 ]]
                return "Daydream";
            end;
            v240.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2390 ]]
                return "";
            end;
            v240.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2391 ]]
                return "rbxassetid://2993241780";
            end;
            v240.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2392 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v240.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2393 ]]
                return "rbxassetid://11508937191";
            end;
            v240.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2394 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v240;
        end)()))
        p_u_3:add_dance_for_id(237, ((function() --[[ Line: 2397 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v241 = p_u_4.DanceInfoBase:new()
            v241.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2399 ]]
                return "Getting Lucky!";
            end;
            v241.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2400 ]]
                return "";
            end;
            v241.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2401 ]]
                return "rbxassetid://2993990427";
            end;
            v241.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2402 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v241.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2403 ]]
                return "rbxassetid://11508939545";
            end;
            v241.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2404 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v241;
        end)()))
        p_u_3:add_dance_for_id(238, ((function() --[[ Line: 2407 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v242 = p_u_4.DanceInfoBase:new()
            v242.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2409 ]]
                return "Tranquility";
            end;
            v242.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2410 ]]
                return "";
            end;
            v242.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2411 ]]
                return "rbxassetid://2993990385";
            end;
            v242.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2412 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v242.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2413 ]]
                return "rbxassetid://11508942511";
            end;
            v242.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2414 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v242;
        end)()))
        p_u_3:add_dance_for_id(239, ((function() --[[ Line: 2417 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v243 = p_u_4.DanceInfoBase:new()
            v243.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2419 ]]
                return "Leilt Elomr";
            end;
            v243.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2420 ]]
                return "";
            end;
            v243.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2421 ]]
                return "rbxassetid://2993990385";
            end;
            v243.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2422 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v243.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2423 ]]
                return "rbxassetid://11508947023";
            end;
            v243.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2424 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v243;
        end)()))
        p_u_3:add_dance_for_id(240, ((function() --[[ Line: 2427 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v244 = p_u_4.DanceInfoBase:new()
            v244.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2429 ]]
                return "Oh Boy Oh Boy Oh Boy";
            end;
            v244.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2430 ]]
                return "";
            end;
            v244.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2431 ]]
                return "rbxassetid://2993990346";
            end;
            v244.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2432 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v244.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2433 ]]
                return "rbxassetid://11508949402";
            end;
            v244.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2434 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v244;
        end)()))
        p_u_3:add_dance_for_id(241, ((function() --[[ Line: 2437 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v245 = p_u_4.DanceInfoBase:new()
            v245.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2439 ]]
                return "Baker\'s Shuffle";
            end;
            v245.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2440 ]]
                return "";
            end;
            v245.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2441 ]]
                return "rbxassetid://2993990307";
            end;
            v245.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2442 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v245.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2443 ]]
                return "rbxassetid://11832015397";
            end;
            v245.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2444 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v245;
        end)()))
        p_u_3:add_dance_for_id(242, ((function() --[[ Line: 2447 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v246 = p_u_4.DanceInfoBase:new()
            v246.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2449 ]]
                return "Fish Outta Water";
            end;
            v246.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2450 ]]
                return "";
            end;
            v246.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2451 ]]
                return "rbxassetid://2993990307";
            end;
            v246.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2452 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v246.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2453 ]]
                return "rbxassetid://12101762378";
            end;
            v246.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2454 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v246;
        end)()))
        p_u_3:add_dance_for_id(243, ((function() --[[ Line: 2457 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v247 = p_u_4.DanceInfoBase:new()
            v247.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2459 ]]
                return "Overdrive";
            end;
            v247.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2460 ]]
                return "";
            end;
            v247.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2461 ]]
                return "rbxassetid://2993241780";
            end;
            v247.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2462 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v247.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2463 ]]
                return "rbxassetid://13865049120";
            end;
            v247.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2464 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v247;
        end)()))
        p_u_3:add_dance_for_id(244, ((function() --[[ Line: 2467 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v248 = p_u_4.DanceInfoBase:new()
            v248.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2469 ]]
                return "Kick \'n\' Swish";
            end;
            v248.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2470 ]]
                return "";
            end;
            v248.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2471 ]]
                return "rbxassetid://2993990427";
            end;
            v248.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2472 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v248.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2473 ]]
                return "rbxassetid://13865062094";
            end;
            v248.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2474 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v248;
        end)()))
        p_u_3:add_dance_for_id(245, ((function() --[[ Line: 2477 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v249 = p_u_4.DanceInfoBase:new()
            v249.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2479 ]]
                return "Caramelldansen";
            end;
            v249.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2480 ]]
                return "";
            end;
            v249.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2481 ]]
                return "rbxassetid://2993990385";
            end;
            v249.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2482 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v249.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2483 ]]
                return "rbxassetid://15373953149";
            end;
            v249.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2484 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v249;
        end)()))
        p_u_3:add_dance_for_id(246, ((function() --[[ Line: 2487 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v250 = p_u_4.DanceInfoBase:new()
            v250.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2489 ]]
                return "GLiTcH3D";
            end;
            v250.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2490 ]]
                return "";
            end;
            v250.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2491 ]]
                return "rbxassetid://2993990346";
            end;
            v250.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2492 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v250.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2493 ]]
                return "rbxassetid://15373957874";
            end;
            v250.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2494 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Combo;
            end;
            return v250;
        end)()))
        p_u_3:add_dance_for_id(247, ((function() --[[ Line: 2497 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v251 = p_u_4.DanceInfoBase:new()
            v251.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2499 ]]
                return "Da Griddy";
            end;
            v251.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2500 ]]
                return "";
            end;
            v251.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2501 ]]
                return "rbxassetid://2993990307";
            end;
            v251.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2502 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v251.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2503 ]]
                return "rbxassetid://15373965029";
            end;
            v251.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2504 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v251;
        end)()))
        p_u_3:add_dance_for_id(248, ((function() --[[ Line: 2507 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_1 ]]
            local v252 = p_u_4.DanceInfoBase:new()
            v252.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2509 ]]
                return "Applejacks";
            end;
            v252.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2510 ]]
                return "";
            end;
            v252.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2511 ]]
                return "rbxassetid://2993241780";
            end;
            v252.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2512 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2.Epic;
            end;
            v252.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2513 ]]
                return "rbxassetid://16319218225";
            end;
            v252.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2514 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Standard;
            end;
            return v252;
        end)()))
        local function _(p253, p_u_254, p_u_255, p_u_256, p_u_257, p_u_258) --[[ Name: create_dance ]] --[[ Line: 2518 ]]
            --[[ Upvalues: (copy 1): p_u_3, (copy 2): p_u_4 ]]
            p_u_3:add_dance_for_id(p253, ((function() --[[ Line: 2519 ]]
                --[[ Upvalues: (ref 1): p_u_4, (copy 2): p_u_254, (copy 3): p_u_255, (copy 4): p_u_256, (copy 5): p_u_257, (copy 6): p_u_258 ]]
                local v259 = p_u_4.DanceInfoBase:new()
                v259.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                    --[[ Upvalues: (ref 1): p_u_254 ]]
                    return p_u_254;
                end;
                v259.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                    return "";
                end;
                v259.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                    --[[ Upvalues: (ref 1): p_u_255 ]]
                    return p_u_255;
                end;
                v259.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                    --[[ Upvalues: (ref 1): p_u_256 ]]
                    return p_u_256;
                end;
                v259.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                    --[[ Upvalues: (ref 1): p_u_257 ]]
                    return p_u_257;
                end;
                v259.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                    --[[ Upvalues: (ref 1): p_u_258 ]]
                    return p_u_258;
                end;
                return v259;
            end)()))
        end;
        local l_Epic_0 = v_u_2.Epic
        local l_OnMiss_0 = v_u_1.OnMiss
        local v_u_260 = "Snapshot Selfies"
        local v_u_261 = "rbxassetid://2993241780"
        local v_u_262 = "rbxassetid://16820831829"
        p_u_3:add_dance_for_id(249, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_260, (copy 3): v_u_261, (copy 4): l_Epic_0, (copy 5): v_u_262, (copy 6): l_OnMiss_0 ]]
            local v263 = p_u_4.DanceInfoBase:new()
            v263.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_260 ]]
                return v_u_260;
            end;
            v263.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v263.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_261 ]]
                return v_u_261;
            end;
            v263.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_0 ]]
                return l_Epic_0;
            end;
            v263.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_262 ]]
                return v_u_262;
            end;
            v263.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_0 ]]
                return l_OnMiss_0;
            end;
            return v263;
        end)()))
        local l_Epic_1 = v_u_2.Epic
        local l_Standard_0 = v_u_1.Standard
        local v_u_264 = "Freedom Wheels"
        local v_u_265 = "rbxassetid://2993990427"
        local v_u_266 = "rbxassetid://16630398263"
        p_u_3:add_dance_for_id(250, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_264, (copy 3): v_u_265, (copy 4): l_Epic_1, (copy 5): v_u_266, (copy 6): l_Standard_0 ]]
            local v267 = p_u_4.DanceInfoBase:new()
            v267.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_264 ]]
                return v_u_264;
            end;
            v267.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v267.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_265 ]]
                return v_u_265;
            end;
            v267.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_1 ]]
                return l_Epic_1;
            end;
            v267.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_266 ]]
                return v_u_266;
            end;
            v267.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_0 ]]
                return l_Standard_0;
            end;
            return v267;
        end)()))
        local l_Epic_2 = v_u_2.Epic
        local l_Standard_1 = v_u_1.Standard
        local v_u_268 = "Leave the Door Open..."
        local v_u_269 = "rbxassetid://2993990385"
        local v_u_270 = "rbxassetid://16630401233"
        p_u_3:add_dance_for_id(251, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_268, (copy 3): v_u_269, (copy 4): l_Epic_2, (copy 5): v_u_270, (copy 6): l_Standard_1 ]]
            local v271 = p_u_4.DanceInfoBase:new()
            v271.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_268 ]]
                return v_u_268;
            end;
            v271.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v271.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_269 ]]
                return v_u_269;
            end;
            v271.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_2 ]]
                return l_Epic_2;
            end;
            v271.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_270 ]]
                return v_u_270;
            end;
            v271.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_1 ]]
                return l_Standard_1;
            end;
            return v271;
        end)()))
        local l_Epic_3 = v_u_2.Epic
        local l_Standard_2 = v_u_1.Standard
        local v_u_272 = "Let it Go!"
        local v_u_273 = "rbxassetid://2993990346"
        local v_u_274 = "rbxassetid://16630405236"
        p_u_3:add_dance_for_id(252, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_272, (copy 3): v_u_273, (copy 4): l_Epic_3, (copy 5): v_u_274, (copy 6): l_Standard_2 ]]
            local v275 = p_u_4.DanceInfoBase:new()
            v275.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_272 ]]
                return v_u_272;
            end;
            v275.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v275.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_273 ]]
                return v_u_273;
            end;
            v275.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_3 ]]
                return l_Epic_3;
            end;
            v275.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_274 ]]
                return v_u_274;
            end;
            v275.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_2 ]]
                return l_Standard_2;
            end;
            return v275;
        end)()))
        local l_Epic_4 = v_u_2.Epic
        local l_OnMiss_1 = v_u_1.OnMiss
        local v_u_276 = "Life into Pieces..."
        local v_u_277 = "rbxassetid://2993990307"
        local v_u_278 = "rbxassetid://17073290867"
        p_u_3:add_dance_for_id(253, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_276, (copy 3): v_u_277, (copy 4): l_Epic_4, (copy 5): v_u_278, (copy 6): l_OnMiss_1 ]]
            local v279 = p_u_4.DanceInfoBase:new()
            v279.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_276 ]]
                return v_u_276;
            end;
            v279.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v279.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_277 ]]
                return v_u_277;
            end;
            v279.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_4 ]]
                return l_Epic_4;
            end;
            v279.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_278 ]]
                return v_u_278;
            end;
            v279.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_1 ]]
                return l_OnMiss_1;
            end;
            return v279;
        end)()))
        local l_Epic_5 = v_u_2.Epic
        local l_OnMiss_2 = v_u_1.OnMiss
        local v_u_280 = "Posessed"
        local v_u_281 = "rbxassetid://2993241780"
        local v_u_282 = "rbxassetid://17085565408"
        p_u_3:add_dance_for_id(254, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_280, (copy 3): v_u_281, (copy 4): l_Epic_5, (copy 5): v_u_282, (copy 6): l_OnMiss_2 ]]
            local v283 = p_u_4.DanceInfoBase:new()
            v283.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_280 ]]
                return v_u_280;
            end;
            v283.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v283.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_281 ]]
                return v_u_281;
            end;
            v283.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_5 ]]
                return l_Epic_5;
            end;
            v283.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_282 ]]
                return v_u_282;
            end;
            v283.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_2 ]]
                return l_OnMiss_2;
            end;
            return v283;
        end)()))
        local l_Epic_6 = v_u_2.Epic
        local l_Standard_3 = v_u_1.Standard
        local v_u_284 = "Blasting off again!"
        local v_u_285 = "rbxassetid://2993990427"
        local v_u_286 = "rbxassetid://17618290032"
        p_u_3:add_dance_for_id(255, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_284, (copy 3): v_u_285, (copy 4): l_Epic_6, (copy 5): v_u_286, (copy 6): l_Standard_3 ]]
            local v287 = p_u_4.DanceInfoBase:new()
            v287.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_284 ]]
                return v_u_284;
            end;
            v287.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v287.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_285 ]]
                return v_u_285;
            end;
            v287.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_6 ]]
                return l_Epic_6;
            end;
            v287.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_286 ]]
                return v_u_286;
            end;
            v287.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_3 ]]
                return l_Standard_3;
            end;
            return v287;
        end)()))
        local l_Epic_7 = v_u_2.Epic
        local l_Combo_0 = v_u_1.Combo
        local v_u_288 = "Boogie Bomb"
        local v_u_289 = "rbxassetid://2993990385"
        local v_u_290 = "rbxassetid://17737830039"
        p_u_3:add_dance_for_id(256, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_288, (copy 3): v_u_289, (copy 4): l_Epic_7, (copy 5): v_u_290, (copy 6): l_Combo_0 ]]
            local v291 = p_u_4.DanceInfoBase:new()
            v291.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_288 ]]
                return v_u_288;
            end;
            v291.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v291.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_289 ]]
                return v_u_289;
            end;
            v291.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_7 ]]
                return l_Epic_7;
            end;
            v291.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_290 ]]
                return v_u_290;
            end;
            v291.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_0 ]]
                return l_Combo_0;
            end;
            return v291;
        end)()))
        local l_Epic_8 = v_u_2.Epic
        local l_Combo_1 = v_u_1.Combo
        local v_u_292 = "Criss-Cross Toprock"
        local v_u_293 = "rbxassetid://2993990346"
        local v_u_294 = "rbxassetid://17737834633"
        p_u_3:add_dance_for_id(257, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_292, (copy 3): v_u_293, (copy 4): l_Epic_8, (copy 5): v_u_294, (copy 6): l_Combo_1 ]]
            local v295 = p_u_4.DanceInfoBase:new()
            v295.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_292 ]]
                return v_u_292;
            end;
            v295.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v295.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_293 ]]
                return v_u_293;
            end;
            v295.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_8 ]]
                return l_Epic_8;
            end;
            v295.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_294 ]]
                return v_u_294;
            end;
            v295.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_1 ]]
                return l_Combo_1;
            end;
            return v295;
        end)()))
        local l_Epic_9 = v_u_2.Epic
        local l_Standard_4 = v_u_1.Standard
        local v_u_296 = "Deep Dab"
        local v_u_297 = "rbxassetid://2993990307"
        local v_u_298 = "rbxassetid://17737836987"
        p_u_3:add_dance_for_id(258, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_296, (copy 3): v_u_297, (copy 4): l_Epic_9, (copy 5): v_u_298, (copy 6): l_Standard_4 ]]
            local v299 = p_u_4.DanceInfoBase:new()
            v299.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_296 ]]
                return v_u_296;
            end;
            v299.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v299.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_297 ]]
                return v_u_297;
            end;
            v299.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_9 ]]
                return l_Epic_9;
            end;
            v299.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_298 ]]
                return v_u_298;
            end;
            v299.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_4 ]]
                return l_Standard_4;
            end;
            return v299;
        end)()))
        local l_Epic_10 = v_u_2.Epic
        local l_Standard_5 = v_u_1.Standard
        local v_u_300 = "Downtown Funk"
        local v_u_301 = "rbxassetid://2993241780"
        local v_u_302 = "rbxassetid://17737839766"
        p_u_3:add_dance_for_id(259, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_300, (copy 3): v_u_301, (copy 4): l_Epic_10, (copy 5): v_u_302, (copy 6): l_Standard_5 ]]
            local v303 = p_u_4.DanceInfoBase:new()
            v303.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_300 ]]
                return v_u_300;
            end;
            v303.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v303.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_301 ]]
                return v_u_301;
            end;
            v303.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_10 ]]
                return l_Epic_10;
            end;
            v303.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_302 ]]
                return v_u_302;
            end;
            v303.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_5 ]]
                return l_Standard_5;
            end;
            return v303;
        end)()))
        local l_Epic_11 = v_u_2.Epic
        local l_Standard_6 = v_u_1.Standard
        local v_u_304 = "Dragon\'s Dance"
        local v_u_305 = "rbxassetid://2993990427"
        local v_u_306 = "rbxassetid://17737842410"
        p_u_3:add_dance_for_id(260, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_304, (copy 3): v_u_305, (copy 4): l_Epic_11, (copy 5): v_u_306, (copy 6): l_Standard_6 ]]
            local v307 = p_u_4.DanceInfoBase:new()
            v307.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_304 ]]
                return v_u_304;
            end;
            v307.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v307.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_305 ]]
                return v_u_305;
            end;
            v307.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_11 ]]
                return l_Epic_11;
            end;
            v307.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_306 ]]
                return v_u_306;
            end;
            v307.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_6 ]]
                return l_Standard_6;
            end;
            return v307;
        end)()))
        local l_Epic_12 = v_u_2.Epic
        local l_Combo_2 = v_u_1.Combo
        local v_u_308 = "Drum Major"
        local v_u_309 = "rbxassetid://2993990385"
        local v_u_310 = "rbxassetid://17737844796"
        p_u_3:add_dance_for_id(261, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_308, (copy 3): v_u_309, (copy 4): l_Epic_12, (copy 5): v_u_310, (copy 6): l_Combo_2 ]]
            local v311 = p_u_4.DanceInfoBase:new()
            v311.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_308 ]]
                return v_u_308;
            end;
            v311.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v311.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_309 ]]
                return v_u_309;
            end;
            v311.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_12 ]]
                return l_Epic_12;
            end;
            v311.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_310 ]]
                return v_u_310;
            end;
            v311.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_2 ]]
                return l_Combo_2;
            end;
            return v311;
        end)()))
        local l_Epic_13 = v_u_2.Epic
        local l_Combo_3 = v_u_1.Combo
        local v_u_312 = "Flippin\' Incredible"
        local v_u_313 = "rbxassetid://2993990346"
        local v_u_314 = "rbxassetid://17737846997"
        p_u_3:add_dance_for_id(262, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_312, (copy 3): v_u_313, (copy 4): l_Epic_13, (copy 5): v_u_314, (copy 6): l_Combo_3 ]]
            local v315 = p_u_4.DanceInfoBase:new()
            v315.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_312 ]]
                return v_u_312;
            end;
            v315.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v315.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_313 ]]
                return v_u_313;
            end;
            v315.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_13 ]]
                return l_Epic_13;
            end;
            v315.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_314 ]]
                return v_u_314;
            end;
            v315.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_3 ]]
                return l_Combo_3;
            end;
            return v315;
        end)()))
        local l_Epic_14 = v_u_2.Epic
        local l_Standard_7 = v_u_1.Standard
        local v_u_316 = "Hand-Crafted Geometry"
        local v_u_317 = "rbxassetid://2993990307"
        local v_u_318 = "rbxassetid://17737849506"
        p_u_3:add_dance_for_id(263, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_316, (copy 3): v_u_317, (copy 4): l_Epic_14, (copy 5): v_u_318, (copy 6): l_Standard_7 ]]
            local v319 = p_u_4.DanceInfoBase:new()
            v319.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_316 ]]
                return v_u_316;
            end;
            v319.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v319.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_317 ]]
                return v_u_317;
            end;
            v319.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_14 ]]
                return l_Epic_14;
            end;
            v319.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_318 ]]
                return v_u_318;
            end;
            v319.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_7 ]]
                return l_Standard_7;
            end;
            return v319;
        end)()))
        local l_Epic_15 = v_u_2.Epic
        local l_Standard_8 = v_u_1.Standard
        local v_u_320 = "House Party"
        local v_u_321 = "rbxassetid://2993241780"
        local v_u_322 = "rbxassetid://17737851950"
        p_u_3:add_dance_for_id(264, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_320, (copy 3): v_u_321, (copy 4): l_Epic_15, (copy 5): v_u_322, (copy 6): l_Standard_8 ]]
            local v323 = p_u_4.DanceInfoBase:new()
            v323.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_320 ]]
                return v_u_320;
            end;
            v323.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v323.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_321 ]]
                return v_u_321;
            end;
            v323.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_15 ]]
                return l_Epic_15;
            end;
            v323.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_322 ]]
                return v_u_322;
            end;
            v323.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_8 ]]
                return l_Standard_8;
            end;
            return v323;
        end)()))
        local l_Epic_16 = v_u_2.Epic
        local l_Standard_9 = v_u_1.Standard
        local v_u_324 = "New Jack Swing"
        local v_u_325 = "rbxassetid://2993990427"
        local v_u_326 = "rbxassetid://17737854306"
        p_u_3:add_dance_for_id(265, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_324, (copy 3): v_u_325, (copy 4): l_Epic_16, (copy 5): v_u_326, (copy 6): l_Standard_9 ]]
            local v327 = p_u_4.DanceInfoBase:new()
            v327.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_324 ]]
                return v_u_324;
            end;
            v327.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v327.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_325 ]]
                return v_u_325;
            end;
            v327.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_16 ]]
                return l_Epic_16;
            end;
            v327.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_326 ]]
                return v_u_326;
            end;
            v327.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_9 ]]
                return l_Standard_9;
            end;
            return v327;
        end)()))
        local l_Epic_17 = v_u_2.Epic
        local l_Standard_10 = v_u_1.Standard
        local v_u_328 = "Party Starter"
        local v_u_329 = "rbxassetid://2993990385"
        local v_u_330 = "rbxassetid://17737856784"
        p_u_3:add_dance_for_id(266, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_328, (copy 3): v_u_329, (copy 4): l_Epic_17, (copy 5): v_u_330, (copy 6): l_Standard_10 ]]
            local v331 = p_u_4.DanceInfoBase:new()
            v331.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_328 ]]
                return v_u_328;
            end;
            v331.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v331.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_329 ]]
                return v_u_329;
            end;
            v331.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_17 ]]
                return l_Epic_17;
            end;
            v331.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_330 ]]
                return v_u_330;
            end;
            v331.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_10 ]]
                return l_Standard_10;
            end;
            return v331;
        end)()))
        local l_Epic_18 = v_u_2.Epic
        local l_Combo_4 = v_u_1.Combo
        local v_u_332 = "Springloaded"
        local v_u_333 = "rbxassetid://2993990346"
        local v_u_334 = "rbxassetid://17737859320"
        p_u_3:add_dance_for_id(267, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_332, (copy 3): v_u_333, (copy 4): l_Epic_18, (copy 5): v_u_334, (copy 6): l_Combo_4 ]]
            local v335 = p_u_4.DanceInfoBase:new()
            v335.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_332 ]]
                return v_u_332;
            end;
            v335.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v335.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_333 ]]
                return v_u_333;
            end;
            v335.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_18 ]]
                return l_Epic_18;
            end;
            v335.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_334 ]]
                return v_u_334;
            end;
            v335.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_4 ]]
                return l_Combo_4;
            end;
            return v335;
        end)()))
        local l_Epic_19 = v_u_2.Epic
        local l_Standard_11 = v_u_1.Standard
        local v_u_336 = "Stardust Ballet"
        local v_u_337 = "rbxassetid://2993990307"
        local v_u_338 = "rbxassetid://17737861347"
        p_u_3:add_dance_for_id(268, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_336, (copy 3): v_u_337, (copy 4): l_Epic_19, (copy 5): v_u_338, (copy 6): l_Standard_11 ]]
            local v339 = p_u_4.DanceInfoBase:new()
            v339.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_336 ]]
                return v_u_336;
            end;
            v339.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v339.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_337 ]]
                return v_u_337;
            end;
            v339.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_19 ]]
                return l_Epic_19;
            end;
            v339.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_338 ]]
                return v_u_338;
            end;
            v339.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_11 ]]
                return l_Standard_11;
            end;
            return v339;
        end)()))
        local l_Epic_20 = v_u_2.Epic
        local l_Standard_12 = v_u_1.Standard
        local v_u_340 = "Tai Chi"
        local v_u_341 = "rbxassetid://2993241780"
        local v_u_342 = "rbxassetid://17737863276"
        p_u_3:add_dance_for_id(269, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_340, (copy 3): v_u_341, (copy 4): l_Epic_20, (copy 5): v_u_342, (copy 6): l_Standard_12 ]]
            local v343 = p_u_4.DanceInfoBase:new()
            v343.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_340 ]]
                return v_u_340;
            end;
            v343.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v343.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_341 ]]
                return v_u_341;
            end;
            v343.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_20 ]]
                return l_Epic_20;
            end;
            v343.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_342 ]]
                return v_u_342;
            end;
            v343.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_12 ]]
                return l_Standard_12;
            end;
            return v343;
        end)()))
        local l_Epic_21 = v_u_2.Epic
        local l_Combo_5 = v_u_1.Combo
        local v_u_344 = "Track Star"
        local v_u_345 = "rbxassetid://2993990427"
        local v_u_346 = "rbxassetid://17737866199"
        p_u_3:add_dance_for_id(270, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_344, (copy 3): v_u_345, (copy 4): l_Epic_21, (copy 5): v_u_346, (copy 6): l_Combo_5 ]]
            local v347 = p_u_4.DanceInfoBase:new()
            v347.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_344 ]]
                return v_u_344;
            end;
            v347.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v347.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_345 ]]
                return v_u_345;
            end;
            v347.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_21 ]]
                return l_Epic_21;
            end;
            v347.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_346 ]]
                return v_u_346;
            end;
            v347.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_5 ]]
                return l_Combo_5;
            end;
            return v347;
        end)()))
        local l_Epic_22 = v_u_2.Epic
        local l_Combo_6 = v_u_1.Combo
        local v_u_348 = "Vogue Drop"
        local v_u_349 = "rbxassetid://2993990385"
        local v_u_350 = "rbxassetid://17737868308"
        p_u_3:add_dance_for_id(271, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_348, (copy 3): v_u_349, (copy 4): l_Epic_22, (copy 5): v_u_350, (copy 6): l_Combo_6 ]]
            local v351 = p_u_4.DanceInfoBase:new()
            v351.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_348 ]]
                return v_u_348;
            end;
            v351.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v351.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_349 ]]
                return v_u_349;
            end;
            v351.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_22 ]]
                return l_Epic_22;
            end;
            v351.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_350 ]]
                return v_u_350;
            end;
            v351.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_6 ]]
                return l_Combo_6;
            end;
            return v351;
        end)()))
        local l_Epic_23 = v_u_2.Epic
        local l_Standard_13 = v_u_1.Standard
        local v_u_352 = "Work It"
        local v_u_353 = "rbxassetid://2993990346"
        local v_u_354 = "rbxassetid://17737871368"
        p_u_3:add_dance_for_id(272, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_352, (copy 3): v_u_353, (copy 4): l_Epic_23, (copy 5): v_u_354, (copy 6): l_Standard_13 ]]
            local v355 = p_u_4.DanceInfoBase:new()
            v355.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_352 ]]
                return v_u_352;
            end;
            v355.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v355.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_353 ]]
                return v_u_353;
            end;
            v355.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_23 ]]
                return l_Epic_23;
            end;
            v355.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_354 ]]
                return v_u_354;
            end;
            v355.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_13 ]]
                return l_Standard_13;
            end;
            return v355;
        end)()))
        local l_Epic_24 = v_u_2.Epic
        local l_Standard_14 = v_u_1.Standard
        local v_u_356 = "9mm"
        local v_u_357 = "rbxassetid://2993990307"
        local v_u_358 = "rbxassetid://17748967192"
        p_u_3:add_dance_for_id(273, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_356, (copy 3): v_u_357, (copy 4): l_Epic_24, (copy 5): v_u_358, (copy 6): l_Standard_14 ]]
            local v359 = p_u_4.DanceInfoBase:new()
            v359.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_356 ]]
                return v_u_356;
            end;
            v359.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v359.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_357 ]]
                return v_u_357;
            end;
            v359.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_24 ]]
                return l_Epic_24;
            end;
            v359.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_358 ]]
                return v_u_358;
            end;
            v359.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_14 ]]
                return l_Standard_14;
            end;
            return v359;
        end)()))
        local l_Epic_25 = v_u_2.Epic
        local l_OnMiss_3 = v_u_1.OnMiss
        local v_u_360 = "Levitated"
        local v_u_361 = "rbxassetid://2993990346"
        local v_u_362 = "rbxassetid://17772840959"
        p_u_3:add_dance_for_id(274, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_360, (copy 3): v_u_361, (copy 4): l_Epic_25, (copy 5): v_u_362, (copy 6): l_OnMiss_3 ]]
            local v363 = p_u_4.DanceInfoBase:new()
            v363.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_360 ]]
                return v_u_360;
            end;
            v363.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v363.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_361 ]]
                return v_u_361;
            end;
            v363.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_25 ]]
                return l_Epic_25;
            end;
            v363.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_362 ]]
                return v_u_362;
            end;
            v363.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_3 ]]
                return l_OnMiss_3;
            end;
            return v363;
        end)()))
        local l_Epic_26 = v_u_2.Epic
        local l_Standard_15 = v_u_1.Standard
        local v_u_364 = "Walkin\' & Strollin\'"
        local v_u_365 = "rbxassetid://2993990385"
        local v_u_366 = "rbxassetid://18336358473"
        p_u_3:add_dance_for_id(275, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_364, (copy 3): v_u_365, (copy 4): l_Epic_26, (copy 5): v_u_366, (copy 6): l_Standard_15 ]]
            local v367 = p_u_4.DanceInfoBase:new()
            v367.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_364 ]]
                return v_u_364;
            end;
            v367.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v367.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_365 ]]
                return v_u_365;
            end;
            v367.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_26 ]]
                return l_Epic_26;
            end;
            v367.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_366 ]]
                return v_u_366;
            end;
            v367.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_15 ]]
                return l_Standard_15;
            end;
            return v367;
        end)()))
        local l_Epic_27 = v_u_2.Epic
        local l_Combo_7 = v_u_1.Combo
        local v_u_368 = "Rude Attitude"
        local v_u_369 = "rbxassetid://2993990427"
        local v_u_370 = "rbxassetid://18446914672"
        p_u_3:add_dance_for_id(276, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_368, (copy 3): v_u_369, (copy 4): l_Epic_27, (copy 5): v_u_370, (copy 6): l_Combo_7 ]]
            local v371 = p_u_4.DanceInfoBase:new()
            v371.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_368 ]]
                return v_u_368;
            end;
            v371.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v371.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_369 ]]
                return v_u_369;
            end;
            v371.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_27 ]]
                return l_Epic_27;
            end;
            v371.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_370 ]]
                return v_u_370;
            end;
            v371.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_7 ]]
                return l_Combo_7;
            end;
            return v371;
        end)()))
        local l_Epic_28 = v_u_2.Epic
        local l_Standard_16 = v_u_1.Standard
        local v_u_372 = "Cruisin\' All Night"
        local v_u_373 = "rbxassetid://2993241780"
        local v_u_374 = "rbxassetid://18446930209"
        p_u_3:add_dance_for_id(277, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_372, (copy 3): v_u_373, (copy 4): l_Epic_28, (copy 5): v_u_374, (copy 6): l_Standard_16 ]]
            local v375 = p_u_4.DanceInfoBase:new()
            v375.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_372 ]]
                return v_u_372;
            end;
            v375.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v375.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_373 ]]
                return v_u_373;
            end;
            v375.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_28 ]]
                return l_Epic_28;
            end;
            v375.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_374 ]]
                return v_u_374;
            end;
            v375.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Standard_16 ]]
                return l_Standard_16;
            end;
            return v375;
        end)()))
        local l_Epic_29 = v_u_2.Epic
        local l_Combo_8 = v_u_1.Combo
        local v_u_376 = "Down Funky"
        local v_u_377 = "rbxassetid://2993990307"
        local v_u_378 = "rbxassetid://18446950521"
        p_u_3:add_dance_for_id(278, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_376, (copy 3): v_u_377, (copy 4): l_Epic_29, (copy 5): v_u_378, (copy 6): l_Combo_8 ]]
            local v379 = p_u_4.DanceInfoBase:new()
            v379.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_376 ]]
                return v_u_376;
            end;
            v379.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v379.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_377 ]]
                return v_u_377;
            end;
            v379.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_29 ]]
                return l_Epic_29;
            end;
            v379.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_378 ]]
                return v_u_378;
            end;
            v379.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_8 ]]
                return l_Combo_8;
            end;
            return v379;
        end)()))
        local l_Epic_30 = v_u_2.Epic
        local l_Combo_9 = v_u_1.Combo
        local v_u_380 = "The DVD Player"
        local v_u_381 = "rbxassetid://2993990346"
        local v_u_382 = "rbxassetid://18447162872"
        p_u_3:add_dance_for_id(279, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_380, (copy 3): v_u_381, (copy 4): l_Epic_30, (copy 5): v_u_382, (copy 6): l_Combo_9 ]]
            local v383 = p_u_4.DanceInfoBase:new()
            v383.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_380 ]]
                return v_u_380;
            end;
            v383.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v383.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_381 ]]
                return v_u_381;
            end;
            v383.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_30 ]]
                return l_Epic_30;
            end;
            v383.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_382 ]]
                return v_u_382;
            end;
            v383.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_9 ]]
                return l_Combo_9;
            end;
            return v383;
        end)()))
        local l_Epic_31 = v_u_2.Epic
        local l_OnMiss_4 = v_u_1.OnMiss
        local v_u_384 = "Pixy Fail"
        local v_u_385 = "rbxassetid://2993990385"
        local v_u_386 = "rbxassetid://18643946890"
        p_u_3:add_dance_for_id(280, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_384, (copy 3): v_u_385, (copy 4): l_Epic_31, (copy 5): v_u_386, (copy 6): l_OnMiss_4 ]]
            local v387 = p_u_4.DanceInfoBase:new()
            v387.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_384 ]]
                return v_u_384;
            end;
            v387.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v387.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_385 ]]
                return v_u_385;
            end;
            v387.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_31 ]]
                return l_Epic_31;
            end;
            v387.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_386 ]]
                return v_u_386;
            end;
            v387.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_4 ]]
                return l_OnMiss_4;
            end;
            return v387;
        end)()))
        local l_Epic_32 = v_u_2.Epic
        local l_OnMiss_5 = v_u_1.OnMiss
        local v_u_388 = "Even Dizzier Fall!"
        local v_u_389 = "rbxassetid://2993990346"
        local v_u_390 = "rbxassetid://94978264945715"
        p_u_3:add_dance_for_id(281, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_388, (copy 3): v_u_389, (copy 4): l_Epic_32, (copy 5): v_u_390, (copy 6): l_OnMiss_5 ]]
            local v391 = p_u_4.DanceInfoBase:new()
            v391.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_388 ]]
                return v_u_388;
            end;
            v391.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v391.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_389 ]]
                return v_u_389;
            end;
            v391.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_32 ]]
                return l_Epic_32;
            end;
            v391.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_390 ]]
                return v_u_390;
            end;
            v391.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_5 ]]
                return l_OnMiss_5;
            end;
            return v391;
        end)()))
        local l_Epic_33 = v_u_2.Epic
        local l_Combo_10 = v_u_1.Combo
        local v_u_392 = "Subway Surfing"
        local v_u_393 = "rbxassetid://2993990307"
        local v_u_394 = "rbxassetid://81244460618052"
        p_u_3:add_dance_for_id(282, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_392, (copy 3): v_u_393, (copy 4): l_Epic_33, (copy 5): v_u_394, (copy 6): l_Combo_10 ]]
            local v395 = p_u_4.DanceInfoBase:new()
            v395.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_392 ]]
                return v_u_392;
            end;
            v395.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v395.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_393 ]]
                return v_u_393;
            end;
            v395.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_33 ]]
                return l_Epic_33;
            end;
            v395.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_394 ]]
                return v_u_394;
            end;
            v395.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_Combo_10 ]]
                return l_Combo_10;
            end;
            return v395;
        end)()))
        local l_Epic_34 = v_u_2.Epic
        local l_OnMiss_6 = v_u_1.OnMiss
        local v_u_396 = "Flying Out!"
        local v_u_397 = "rbxassetid://2993241780"
        local v_u_398 = "rbxassetid://92553667028134"
        p_u_3:add_dance_for_id(283, ((function() --[[ Line: 2519 ]]
            --[[ Upvalues: (copy 1): p_u_4, (copy 2): v_u_396, (copy 3): v_u_397, (copy 4): l_Epic_34, (copy 5): v_u_398, (copy 6): l_OnMiss_6 ]]
            local v399 = p_u_4.DanceInfoBase:new()
            v399.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2521 ]]
                --[[ Upvalues: (ref 1): v_u_396 ]]
                return v_u_396;
            end;
            v399.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 2522 ]]
                return "";
            end;
            v399.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2523 ]]
                --[[ Upvalues: (ref 1): v_u_397 ]]
                return v_u_397;
            end;
            v399.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 2524 ]]
                --[[ Upvalues: (ref 1): l_Epic_34 ]]
                return l_Epic_34;
            end;
            v399.get_assetid = function(_) --[[ Name: get_assetid ]] --[[ Line: 2525 ]]
                --[[ Upvalues: (ref 1): v_u_398 ]]
                return v_u_398;
            end;
            v399.internal_get_dance_type = function(_) --[[ Name: internal_get_dance_type ]] --[[ Line: 2526 ]]
                --[[ Upvalues: (ref 1): l_OnMiss_6 ]]
                return l_OnMiss_6;
            end;
            return v399;
        end)()))
    end
};
